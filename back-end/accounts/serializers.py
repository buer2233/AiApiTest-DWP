from __future__ import annotations

import re

from django.utils import timezone
from rest_framework import serializers

from accounts.models import InvitationCode, UserAccount


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=64)
    password = serializers.CharField(min_length=8, max_length=64, trim_whitespace=False)
    lang = serializers.ChoiceField(choices=["zh_CN", "en_US"], required=False)


class RegisterSerializer(serializers.Serializer):
    invitation_code = serializers.CharField()
    username = serializers.CharField(min_length=3, max_length=64)
    display_name = serializers.CharField(min_length=1, max_length=64, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=64, trim_whitespace=False)
    confirm_password = serializers.CharField(min_length=8, max_length=64, trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        if not USERNAME_RE.match(value):
            raise serializers.ValidationError("账号只能包含字母、数字、下划线、短横线和点。")
        return value

    def validate(self, attrs):
        password = attrs["password"]
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致。"})
        if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise serializers.ValidationError({"password": "密码需至少包含字母和数字。"})
        return attrs


class InvitationCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[UserAccount.Role.ADMIN, UserAccount.Role.MEMBER])
    expires_at = serializers.DateTimeField(required=False)

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("过期时间必须晚于当前时间。")
        return value


class UserSummarySerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = UserAccount
        fields = ["id", "username", "display_name", "role", "permissions", "created_at", "last_login_at"]


class InvitationSummarySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    created_by = serializers.CharField(source="created_by.username")
    used_by = serializers.CharField(source="used_by.username", allow_null=True)

    class Meta:
        model = InvitationCode
        fields = [
            "id",
            "role",
            "status",
            "expires_at",
            "created_by",
            "used_by",
            "used_at",
            "revoked_at",
            "created_at",
        ]

    def get_status(self, obj: InvitationCode) -> str:
        return obj.effective_status
