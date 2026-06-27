"""accounts 后台：管理员在此审批/停用用户（改 status 即同步 is_active）。"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "status",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("status", "role", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

    # 在用户编辑页加入平台属性（status/role）——审批入口
    fieldsets = UserAdmin.fieldsets + (
        ("平台属性", {"fields": ("status", "role")}),
    )
    # 新建用户页加入邮箱与平台属性
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("平台属性", {"fields": ("email", "status", "role")}),
    )
