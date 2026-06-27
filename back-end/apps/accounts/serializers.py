"""accounts 序列化器。"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户信息输出（用于 me 与登录返回）。"""

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "status", "date_joined", "last_login"]


class RegisterSerializer(serializers.ModelSerializer):
    """注册输入校验。

    唯一性与两次密码一致性在视图层显式判定（映射 1001/1002/1003），
    本序列化器负责字段格式、长度与 Django 密码强度校验（映射 1004）。
    """

    # 覆盖默认字段：去掉 ModelSerializer 自带的 UniqueValidator，唯一性交由视图判定
    username = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password_confirm", "status", "role"]
        read_only_fields = ["id", "status", "role"]

    def validate_password(self, value):
        # 触发 Django 密码强度校验（过短/纯数字/常见弱密码等）
        validate_password(value)
        return value

    def create(self, validated_data):
        # 新用户固定 pending + member，不返回 token
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            status=User.STATUS_PENDING,
            role=User.ROLE_MEMBER,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user
