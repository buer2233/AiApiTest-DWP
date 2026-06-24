"""账户认证序列化模块。
本模块负责把用户信息输出给前端，并校验登录请求中的用户名和密码。
登录成功后视图层会基于校验出的 user 创建或复用 DRF Token。
"""

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """平台用户基础信息序列化器。
    仅暴露前端登录态需要的用户 ID、用户名和角色，避免输出密码、邮箱等非必要字段。
    """

    class Meta:
        """绑定用户模型和允许输出的字段。"""

        model = User
        fields = ["id", "username", "role"]


class LoginSerializer(serializers.Serializer):
    """登录请求序列化器。
    校验用户名、密码和用户启用状态，并把认证成功的 user 放入 validated_data。
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        """校验登录凭据。
        Args:
            attrs: 已完成字段级校验的登录参数。
        Returns:
            dict: 原登录参数，并额外包含认证成功的 user。
        Raises:
            serializers.ValidationError: 用户名密码错误或用户被禁用。
        """
        # 使用 Django 认证后端统一校验密码，避免在序列化器中直接处理密码哈希。
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("用户名或密码错误")
        if not user.is_active:
            raise serializers.ValidationError("用户已禁用")
        # 视图层需要复用认证出的用户对象来创建 Token，避免重复查询。
        attrs["user"] = user
        return attrs
