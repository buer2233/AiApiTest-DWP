from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Iterable

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class UserAccountManager(models.Manager):
    def create_user(
        self,
        *,
        username: str,
        password: str,
        role: str,
        display_name: str = "",
        is_active: bool = True,
    ) -> "UserAccount":
        user = self.model(
            username=username,
            display_name=display_name or username,
            role=role,
            is_active=is_active,
        )
        user.set_password(password)
        user.full_clean()
        user.save()
        return user


class UserAccount(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "管理人员"
        MEMBER = "member", "普通成员"

    username = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64, blank=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserAccountManager()

    class Meta:
        db_table = "user_account"
        ordering = ["-created_at", "-id"]

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def permissions(self) -> list[str]:
        if self.role == self.Role.ADMIN:
            return [
                "users:read",
                "invitations:read",
                "invitations:create",
                "invitations:revoke",
            ]
        return ["profile:read"]

    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    def mark_logged_in(self) -> None:
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])

    def __str__(self) -> str:
        return self.username


class InvitationCodeManager(models.Manager):
    def create_plain_code(
        self,
        *,
        role: str,
        created_by: UserAccount,
        expires_at=None,
    ) -> tuple["InvitationCode", str]:
        plain_code = f"INV-{secrets.token_urlsafe(18)}"
        invitation = self.model(
            code_hash=InvitationCode.hash_code(plain_code),
            role=role,
            status=InvitationCode.Status.UNUSED,
            expires_at=expires_at or timezone.now() + timedelta(days=7),
            created_by=created_by,
        )
        invitation.full_clean()
        invitation.save()
        return invitation, plain_code

    def find_by_plain_code(self, plain_code: str) -> "InvitationCode | None":
        return self.filter(code_hash=InvitationCode.hash_code(plain_code)).first()


class InvitationCode(models.Model):
    class Status(models.TextChoices):
        UNUSED = "unused", "未使用"
        USED = "used", "已使用"
        REVOKED = "revoked", "已作废"
        EXPIRED = "expired", "已过期"

    code_hash = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=16, choices=UserAccount.Role.choices, default=UserAccount.Role.MEMBER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNUSED)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(UserAccount, related_name="created_invitations", on_delete=models.PROTECT)
    used_by = models.ForeignKey(
        UserAccount,
        related_name="used_invitations",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        UserAccount,
        related_name="revoked_invitations",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InvitationCodeManager()

    class Meta:
        db_table = "invitation_code"
        ordering = ["-created_at", "-id"]

    @staticmethod
    def hash_code(plain_code: str) -> str:
        return hashlib.sha256(plain_code.encode("utf-8")).hexdigest()

    @property
    def effective_status(self) -> str:
        if self.status == self.Status.UNUSED and self.expires_at < timezone.now():
            return self.Status.EXPIRED
        return self.status

    def can_register(self) -> bool:
        return self.status == self.Status.UNUSED and self.expires_at >= timezone.now()

    def mark_used(self, user: UserAccount) -> None:
        self.status = self.Status.USED
        self.used_by = user
        self.used_at = timezone.now()
        self.save(update_fields=["status", "used_by", "used_at", "updated_at"])

    def revoke(self, user: UserAccount) -> None:
        self.status = self.Status.REVOKED
        self.revoked_by = user
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_by", "revoked_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.role}:{self.effective_status}"
