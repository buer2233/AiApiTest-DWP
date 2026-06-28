from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        DISABLED = "disabled", "Disabled"

    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"

    def can_login(self) -> bool:
        return self.status == self.Status.ACTIVE and self.is_active


class RegistrationInviteCode(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        EXHAUSTED = "exhausted", "Exhausted"
        EXPIRED = "expired", "Expired"

    code = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(User, related_name="created_invite_codes", on_delete=models.PROTECT)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "registration_invite_code"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(max_uses__gte=1), name="invite_code_max_uses_gte_1"),
            models.CheckConstraint(condition=models.Q(used_count__lte=models.F("max_uses")), name="invite_code_used_count_lte_max_uses"),
        ]

    def __str__(self) -> str:
        return self.code

    def refresh_expired_status(self) -> None:
        if self.status == self.Status.ACTIVE and self.expires_at and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status", "updated_at"])

    def is_available(self) -> bool:
        self.refresh_expired_status()
        return self.status == self.Status.ACTIVE and self.used_count < self.max_uses

    def consume(self) -> None:
        self.used_count += 1
        self.last_used_at = timezone.now()
        if self.used_count >= self.max_uses:
            self.status = self.Status.EXHAUSTED
        self.save(update_fields=["used_count", "last_used_at", "status", "updated_at"])
