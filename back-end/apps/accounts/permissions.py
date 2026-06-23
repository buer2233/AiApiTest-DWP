from rest_framework.permissions import BasePermission

from .models import User


class PlatformAccessPermission(BasePermission):
    """Current platform API access: admin and member are intentionally equal."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in User.Role.values
        )


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == User.Role.ADMIN
        )
