from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import AuthSession, SessionRefreshToken


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.COOKIES.get("session_id")
        refresh_jwt = request.COOKIES.get("refresh_token")

        if session_id:
            AuthSession.objects.filter(id=session_id).update(revoked_at=timezone.now())
            SessionRefreshToken.objects.filter(session_id=session_id, revoked_at__isnull=True).update(
                revoked_at=timezone.now()
            )

        # blacklist the refresh token too (optional but recommended)
        if refresh_jwt:
            try:
                RefreshToken(refresh_jwt).blacklist()
            except (TokenError, Exception):
                pass

        res = Response({"success": True})
        res.delete_cookie("access_token", path="/")
        res.delete_cookie("refresh_token", path="/")
        res.delete_cookie("session_id", path="/")
        return res
