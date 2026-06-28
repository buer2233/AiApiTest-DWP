from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """限制 admin 角色或 Django 管理员执行高权限操作。"""

    message = "无权执行该操作"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (getattr(user, "role", "") == "admin" or user.is_staff or user.is_superuser)
        )
