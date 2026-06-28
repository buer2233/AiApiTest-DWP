from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import RegistrationInviteCode, User


@admin.register(User)
class PlatformUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("平台字段", {"fields": ("role", "status")}),)
    list_display = ("username", "email", "role", "status", "is_staff")
    list_filter = ("role", "status", "is_staff")


@admin.register(RegistrationInviteCode)
class RegistrationInviteCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "status", "max_uses", "used_count", "expires_at", "created_by")
    list_filter = ("status",)
    search_fields = ("code",)
