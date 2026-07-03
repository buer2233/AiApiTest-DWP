from __future__ import annotations

from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from accounts.models import UserAccount


def issue_auth_token(user: UserAccount) -> str:
    expires_at = timezone.now() + timedelta(seconds=settings.AUTH_COOKIE_MAX_AGE_SECONDS)
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "iss": settings.AUTH_TOKEN_ISSUER,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.AUTH_TOKEN_SECRET, algorithm="HS256")
