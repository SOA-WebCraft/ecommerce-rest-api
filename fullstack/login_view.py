from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework import status
from rest_framework.views import APIView

from .cookies import cookie_kwargs
from .models import AuthSession, SessionRefreshToken
from .serializers import CustomTokenSerializer


class CookieTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.user  # ✅ FIX: not validated_data["user"]

        refresh_str = serializer.validated_data["refresh"]
        refresh = RefreshToken(refresh_str)

        session = AuthSession.objects.create(
            user=user,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
            ip_address=request.META.get("REMOTE_ADDR"),
            last_seen_at=timezone.now(),
        )

        # Bind sid to both tokens
        refresh["sid"] = str(session.id)
        access = refresh.access_token
        access["sid"] = str(session.id)

        # Track refresh for reuse detection
        SessionRefreshToken.objects.create(session=session, jti=refresh["jti"])

        res = Response({"success": True})
        res.set_cookie("access_token", str(access), **cookie_kwargs())
        res.set_cookie("refresh_token", str(refresh), **cookie_kwargs())
        res.set_cookie("session_id", str(session.id), **cookie_kwargs())
        return res



class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_jwt = request.COOKIES.get("refresh_token")
        session_id = request.COOKIES.get("session_id")

        if not refresh_jwt or not session_id:
            return Response(
                {"detail": "Missing session"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ✅ get active session
        session = (
            AuthSession.objects
            .filter(id=session_id)
            .select_related("user")
            .first()
        )

        if not session or session.revoked_at is not None:
            return Response(
                {"detail": "Session revoked"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            incoming = RefreshToken(refresh_jwt)

            # ========================
            # ✅ SID ENFORCEMENT
            # ========================
            token_sid = incoming.get("sid")
            if not token_sid or str(token_sid) != str(session_id):
                return Response(
                    {"detail": "Session mismatch"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # ========================
            # ✅ REUSE DETECTION
            # ========================
            jti = incoming["jti"]

            record = SessionRefreshToken.objects.filter(
                jti=jti,
                session=session,
            ).first()

            if (record is None or record.revoked_at is not None or record.rotated_at is not None):
                now = timezone.now()
                session.revoked_at = now
                session.save(update_fields=["revoked_at"])

                SessionRefreshToken.objects.filter(session=session,  revoked_at__isnull=True,).update(revoked_at=now)

    # ⭐ OPTIONAL extra safety
                try:
                   incoming.blacklist()
                except Exception:
                   pass

                res = Response(
                    {"detail": "Refresh reuse detected. Session revoked."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

                res.delete_cookie("access_token", path="/")
                res.delete_cookie("refresh_token", path="/")
                res.delete_cookie("session_id", path="/")
                return res

            # ========================
            # ✅ MARK OLD TOKEN ROTATED (single-use)
            # ========================
            record.rotated_at = timezone.now()
            record.save(update_fields=["rotated_at"])

            # ========================
            # ✅ ISSUE NEW TOKENS (CLEAN)
            # ========================
            new_refresh = RefreshToken.for_user(session.user)
            new_refresh["sid"] = str(session.id)

            new_access = new_refresh.access_token
            new_access["sid"] = str(session.id)

            # ========================
            # ✅ TRACK NEW REFRESH
            # ========================
            SessionRefreshToken.objects.create(
                session=session,
                jti=new_refresh["jti"],
            )

            session.last_seen_at = timezone.now()
            session.save(update_fields=["last_seen_at"])

            # ========================
            # ✅ SET COOKIES
            # ========================
            res = Response({"success": True})

            res.set_cookie(
                "access_token",
                str(new_access),
                **cookie_kwargs(),
            )

            res.set_cookie(
                "refresh_token",
                str(new_refresh),
                **cookie_kwargs(),
            )

            return res

        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
