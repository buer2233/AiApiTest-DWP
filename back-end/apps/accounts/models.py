"""accounts 数据模型：自定义 User（含 status/role 与状态不变式）。"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """平台用户主体。

    - status：pending（待审批）/ active（已激活）/ disabled（已停用）。
    - role：admin / member。
    - 不变式：is_active == (status == 'active')，由 save() 强制同步。
    """

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待审批"),
        (STATUS_ACTIVE, "已激活"),
        (STATUS_DISABLED, "已停用"),
    ]

    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "管理员"),
        (ROLE_MEMBER, "成员"),
    ]

    # 覆盖为唯一邮箱（AbstractUser 默认 email 不唯一）
    email = models.EmailField("邮箱", unique=True)
    status = models.CharField(
        "状态", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    role = models.CharField(
        "角色", max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER, db_index=True
    )

    # createsuperuser 时同时要求邮箱
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # 超级用户强制 active + admin，保证可登录 Django Admin
        if self.is_superuser:
            self.status = self.STATUS_ACTIVE
            self.role = self.ROLE_ADMIN
        # 强制状态不变式
        self.is_active = self.status == self.STATUS_ACTIVE
        super().save(*args, **kwargs)
        # 非激活用户（pending/disabled）强制下线：删除其可能存在的 Token
        if not self.is_active:
            from rest_framework.authtoken.models import Token

            Token.objects.filter(user=self).delete()
