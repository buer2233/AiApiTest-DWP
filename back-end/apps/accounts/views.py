"""accounts 视图：注册 / 登录 / 登出 / 当前用户。统一响应见 common。"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError
from rest_framework import status as http_status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BizError
from common.response import BizCode, success

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(APIView):
    """F1 用户注册：公开；创建 pending 用户，不返回 token。"""

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        password_confirm = data.get("password_confirm")

        # 唯一性与一致性优先判定，映射明确业务码
        if username and User.objects.filter(username=username).exists():
            raise BizError(BizCode.USERNAME_TAKEN, "用户名已被占用")
        if email and User.objects.filter(email=email).exists():
            raise BizError(BizCode.EMAIL_TAKEN, "邮箱已被占用")
        if password != password_confirm:
            raise BizError(BizCode.PASSWORD_MISMATCH, "两次密码不一致")

        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            raise BizError(BizCode.VALIDATION_ERROR, "字段校验失败", errors=serializer.errors)
        try:
            user = serializer.save()
        except IntegrityError:
            # 并发注册竞态兜底：唯一约束在数据库层最终拦截，映射回友好业务码
            if User.objects.filter(username=username).exists():
                raise BizError(BizCode.USERNAME_TAKEN, "用户名已被占用")
            raise BizError(BizCode.EMAIL_TAKEN, "邮箱已被占用")
        return success(
            data={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "role": user.role,
            },
            message="注册成功，待管理员审批",
            http_status=http_status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """F2 用户登录：公开；仅 active 用户可登录，返回 token + user。"""

    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            raise BizError(BizCode.VALIDATION_ERROR, "用户名和密码不能为空")

        # 防枚举：用户不存在与密码错误返回完全相同的响应
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise BizError(BizCode.INVALID_CREDENTIALS, "用户名或密码错误")
        if not user.check_password(password):
            raise BizError(BizCode.INVALID_CREDENTIALS, "用户名或密码错误")

        # 密码正确后再判状态
        if user.status == User.STATUS_PENDING:
            raise BizError(
                BizCode.ACCOUNT_PENDING,
                "账号待管理员审批",
                http_status_code=http_status.HTTP_403_FORBIDDEN,
            )
        if user.status == User.STATUS_DISABLED:
            raise BizError(
                BizCode.ACCOUNT_DISABLED,
                "账号已停用，请联系管理员",
                http_status_code=http_status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        update_last_login(None, user)
        return success(
            data={"token": token.key, "user": UserSerializer(user).data},
            message="登录成功",
        )


class LogoutView(APIView):
    """F3 用户登出：删除当前用户 token。"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return success(message="已登出")


class MeView(APIView):
    """F4 当前用户信息。"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success(data=UserSerializer(request.user).data)
