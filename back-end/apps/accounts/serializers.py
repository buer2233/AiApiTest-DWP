from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import RegistrationInviteCode
from common.exceptions import BadRequestError, ConflictError


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "status")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    invite_code = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "两次密码不一致"})
        if User.objects.filter(Q(username=attrs["username"]) | Q(email=attrs["email"])).exists():
            raise ConflictError("duplicate_user", "用户名或邮箱已存在")
        return attrs


class LoginSerializer(serializers.Serializer):
    account = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class InviteCodeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationInviteCode
        fields = ("code", "max_uses", "expires_at")
        extra_kwargs = {
            "code": {"min_length": 6, "max_length": 64, "validators": []},
            "max_uses": {"min_value": 1},
            "expires_at": {"required": False, "allow_null": True},
        }

    def validate_code(self, value):
        if RegistrationInviteCode.objects.filter(code=value).exists():
            raise ConflictError("duplicate_invite_code", "邀请码已存在")
        return value

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("过期时间必须晚于当前时间")
        return value


class InviteCodeSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = RegistrationInviteCode
        fields = (
            "id",
            "code",
            "status",
            "max_uses",
            "used_count",
            "expires_at",
            "created_by",
            "last_used_at",
            "created_at",
            "updated_at",
        )

    def get_created_by(self, obj):
        return {"id": obj.created_by_id, "username": obj.created_by.username}


def get_available_invite(code: str) -> RegistrationInviteCode:
    try:
        invite = RegistrationInviteCode.objects.select_for_update().get(code=code)
    except RegistrationInviteCode.DoesNotExist as exc:
        raise BadRequestError("invalid_invite_code", "邀请码不存在") from exc
    if not invite.is_available():
        raise BadRequestError("invite_code_unavailable", "邀请码不可用")
    return invite
