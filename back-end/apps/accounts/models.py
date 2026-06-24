"""平台用户模型模块。
本模块在 Django 默认用户能力上增加平台角色字段，并保留管理员与普通用户的身份区分。
当前第一版权限基本一致，但角色模型为后续差异化授权和审计留出扩展点。
"""

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """平台用户管理器。
    该管理器只调整超级管理员创建时的默认角色，其他用户创建逻辑继续复用 Django 内置实现。
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """创建超级管理员用户。
        Args:
            username: Django 登录用户名。
            email: 用户邮箱，可为空。
            password: 用户密码，可为空但生产环境应显式提供。
            **extra_fields: 传给 Django 用户模型的额外字段。
        Returns:
            User: 已创建的超级管理员用户。
        """
        # 命令行创建超级管理员时默认标记为平台管理员，避免权限入口判断失效。
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """测试平台用户模型。
    继承 Django AbstractUser 以保留 username/password/is_active 等认证字段，
    并通过 role 区分管理员和普通成员。
    """

    class Role(models.TextChoices):
        """平台内置角色枚举。"""

        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    objects = UserManager()
