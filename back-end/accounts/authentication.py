from __future__ import annotations

import jwt
from django.conf import settings
from rest_framework import status
from rest_framework.authentication import BaseAuthentication

from accounts.exceptions import ApiError
from accounts.models import UserAccount


class CookieJWTAuthentication(BaseAuthentication):
    """从 HttpOnly Cookie 中读取 authToken 并恢复平台用户。"""

    def authenticate(self, request):
        token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not token:
            raise ApiError(
                code="authentication_required",
                message="未登录或登录已过期，请重新登录。",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = jwt.decode(
                token,
                settings.AUTH_TOKEN_SECRET,
                algorithms=["HS256"],
                issuer=settings.AUTH_TOKEN_ISSUER,
            )
            user_id = int(payload["user_id"])
        except Exception as exc:
            raise ApiError(
                code="invalid_or_expired_token",
                message="登录凭据无效或已过期，请重新登录。",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        user = UserAccount.objects.filter(id=user_id, is_active=True).first()
        if user is None:
            raise ApiError(
                code="invalid_or_expired_token",
                message="登录凭据无效或已过期，请重新登录。",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return user, token

    def authenticate_header(self, request) -> str:
        return "Cookie"
