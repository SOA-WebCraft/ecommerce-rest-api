from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import AuthSession


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            auth = super().authenticate(request)
        else:
            raw_token = request.COOKIES.get("access_token")
            if raw_token is None:
                return None
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            auth = (user, validated_token)

        if auth is None:
            return None

        user, token = auth

        # ---- SID CLAIM ENFORCEMENT ----
        sid = token.get("sid")
        if not sid:
            raise exceptions.AuthenticationFailed("Token missing session id (sid).")

        session = AuthSession.objects.filter(id=sid, user=user).only("revoked_at").first()
        if not session or session.revoked_at is not None:
            raise exceptions.AuthenticationFailed("Session revoked.")

        return (user, token)
