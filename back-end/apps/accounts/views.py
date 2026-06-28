from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import RegistrationInviteCode
from apps.accounts.serializers import (
    InviteCodeCreateSerializer,
    InviteCodeSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    get_available_invite,
)
from common.exceptions import BadRequestError, ConflictError
from common.pagination import paginate_queryset
from common.permissions import IsAdminRole
from common.response import error_response, success_response


User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            invite = get_available_invite(data["invite_code"])
        except BadRequestError as exc:
            return error_response(exc.business_code, str(exc.detail), status_code=exc.status_code, details=exc.details)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    role=User.Role.MEMBER,
                    status=User.Status.ACTIVE,
                )
        except IntegrityError as exc:
            raise ConflictError("duplicate_user", "用户名或邮箱已存在") from exc
        invite.consume()
        return success_response(UserSerializer(user).data, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.validated_data["account"].strip()
        password = serializer.validated_data["password"]
        user = User.objects.filter(Q(username=account) | Q(email=account)).first()
        if not user or not check_password(password, user.password):
            return error_response("invalid_credentials", "账号或密码错误", status_code=status.HTTP_401_UNAUTHORIZED)
        if not user.can_login():
            return error_response("user_not_active", "用户状态不允许登录", status_code=status.HTTP_403_FORBIDDEN)
        token, _ = Token.objects.get_or_create(user=user)
        update_last_login(None, user)
        return success_response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        return success_response(None, status_code=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(UserSerializer(request.user).data)


class InviteCodeListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        queryset = RegistrationInviteCode.objects.select_related("created_by").all()
        keyword = request.query_params.get("keyword", "").strip()
        status_value = request.query_params.get("status", "").strip()
        if keyword:
            queryset = queryset.filter(code__icontains=keyword)
        if status_value:
            queryset = queryset.filter(status=status_value)
        page_items, meta = paginate_queryset(request, queryset)
        return success_response(InviteCodeSerializer(page_items, many=True).data, meta=meta)

    def post(self, request):
        serializer = InviteCodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite = serializer.save(created_by=request.user)
        return success_response(InviteCodeSerializer(invite).data, status_code=status.HTTP_201_CREATED)


class InviteCodeDisableView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            invite = RegistrationInviteCode.objects.get(pk=pk)
        except RegistrationInviteCode.DoesNotExist:
            return error_response("not_found", "邀请码不存在", status_code=status.HTTP_404_NOT_FOUND)
        if invite.status != RegistrationInviteCode.Status.ACTIVE:
            raise ConflictError("invalid_invite_status", "当前邀请码状态不可禁用")
        invite.status = RegistrationInviteCode.Status.DISABLED
        invite.save(update_fields=["status", "updated_at"])
        return success_response(InviteCodeSerializer(invite).data)
