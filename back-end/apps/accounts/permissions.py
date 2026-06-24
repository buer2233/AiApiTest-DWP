"""账户权限模块。
本模块集中定义测试平台的角色访问规则，供账号、测试任务和 Jenkins API 复用。
第一版 admin 与 member 都能访问平台，管理员专属权限入口用于后续扩展。
"""

from rest_framework.permissions import BasePermission

from .models import User


class PlatformAccessPermission(BasePermission):
    """平台基础访问权限。
    当前阶段管理员和普通成员权限一致，只要是已认证且角色合法的用户即可访问平台 API。
    """

    def has_permission(self, request, view):
        """判断当前请求是否具备平台访问权限。
        Args:
            request: DRF 请求对象。
            view: 当前被访问的 DRF 视图。
        Returns:
            bool: True 表示用户已认证且角色属于平台已知角色。
        """
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in User.Role.values
        )


class IsPlatformAdmin(BasePermission):
    """平台管理员权限。
    当前作为预留入口，后续需要限制管理类接口时可直接复用该权限类。
    """

    def has_permission(self, request, view):
        """判断当前请求用户是否为平台管理员。
        Args:
            request: DRF 请求对象。
            view: 当前被访问的 DRF 视图。
        Returns:
            bool: True 表示用户已认证且 role 为 admin。
        """
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == User.Role.ADMIN
        )
