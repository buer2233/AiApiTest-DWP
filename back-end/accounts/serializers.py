from __future__ import annotations

import re

from django.utils import timezone
from rest_framework import serializers

from accounts.models import InvitationCode, UserAccount
from common.serializers import ApiErrorResponseSerializer, PaginationMetaSerializer


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
PASSWORD_REQUIREMENT_TEXT = "密码需 8-64 位，至少包含字母和数字"


def build_password_requirement_message(password: str) -> str:
    """按当前密码内容生成可执行的弱密码原因，避免前端猜测复杂度规则。"""
    missing_reasons: list[str] = []
    if len(password) < 8:
        missing_reasons.append("长度不足 8 位")
    if len(password) > 64:
        missing_reasons.append("长度超过 64 位")
    if not any(ch.isalpha() for ch in password):
        missing_reasons.append("缺少字母")
    if not any(ch.isdigit() for ch in password):
        missing_reasons.append("缺少数字")

    if missing_reasons:
        return f"{PASSWORD_REQUIREMENT_TEXT}；当前{'，'.join(missing_reasons)}。"
    return f"{PASSWORD_REQUIREMENT_TEXT}。"


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=64)
    password = serializers.CharField(max_length=64, trim_whitespace=False)
    lang = serializers.ChoiceField(choices=["zh_CN", "en_US"], required=False)


class RegisterSerializer(serializers.Serializer):
    invitation_code = serializers.CharField()
    username = serializers.CharField(min_length=3, max_length=64)
    display_name = serializers.CharField(min_length=1, max_length=64, required=False, allow_blank=True)
    password = serializers.CharField(trim_whitespace=False)
    confirm_password = serializers.CharField(trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        if not USERNAME_RE.match(value):
            raise serializers.ValidationError("账号只能包含字母、数字、下划线、短横线和点。")
        return value

    def validate(self, attrs):
        password = attrs["password"]
        # 先判断两次输入是否一致，避免短密码等复杂度错误覆盖更直接的用户操作问题。
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致。"})
        if len(password) < 8 or len(password) > 64 or not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise serializers.ValidationError({"password": build_password_requirement_message(password)})
        return attrs


class InvitationCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserAccount.Role.choices)
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


class UserDataResponseSerializer(serializers.Serializer):
    data = UserSummarySerializer()


class UserListResponseSerializer(serializers.Serializer):
    data = UserSummarySerializer(many=True)
    meta = PaginationMetaSerializer()


class InvitationDataResponseSerializer(serializers.Serializer):
    data = InvitationSummarySerializer()


class InvitationListResponseSerializer(serializers.Serializer):
    data = InvitationSummarySerializer(many=True)
    meta = PaginationMetaSerializer()


class InvitationCreateDataSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=UserAccount.Role.choices)
    status = serializers.ChoiceField(choices=[choice.value for choice in InvitationCode.Status])
    expires_at = serializers.DateTimeField()
    created_by = serializers.CharField()
    used_by = serializers.CharField(allow_null=True)
    used_at = serializers.DateTimeField(allow_null=True)
    revoked_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    plain_code = serializers.CharField()


class InvitationCreateResponseSerializer(serializers.Serializer):
    data = InvitationCreateDataSerializer()
