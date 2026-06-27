"""通用权限类。"""
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """要求用户为管理员（role=admin 或 is_staff=True）。

    用于用例同步等管理员专属接口；未登录由 IsAuthenticated 先行拦截为 401，
    已登录非管理员在此返回 403。
    """

    message = "无权限执行该操作"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (getattr(user, "role", None) == "admin" or user.is_staff)
        )
