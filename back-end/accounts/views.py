from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.models import InvitationCode, UserAccount
from accounts.serializers import (
    ApiErrorResponseSerializer,
    InvitationCreateResponseSerializer,
    InvitationCreateSerializer,
    InvitationDataResponseSerializer,
    InvitationListResponseSerializer,
    InvitationSummarySerializer,
    UserDataResponseSerializer,
    UserListResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSummarySerializer,
    build_password_requirement_message,
)
from accounts.tokens import issue_auth_token
from common.exceptions import api_error_response
from common.pagination import paginated_response, parse_pagination


def validation_error(serializer) -> Response:
    return api_error_response(
        "validation_error",
        "请求参数校验失败。",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=[serializer.errors],
    )


def has_serializer_error_code(errors, field_name: str, expected_codes: set[str]) -> bool:
    """判断字段级错误码，避免把必填/空值错误误映射为业务语义错误。"""
    field_errors = errors.get(field_name, [])
    if not isinstance(field_errors, list):
        field_errors = [field_errors]
    return any(getattr(error, "code", "") in expected_codes for error in field_errors)


def require_admin(user: UserAccount) -> Response | None:
    if user.role != UserAccount.Role.ADMIN:
        return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
    return None


def register_invitation_error(invitation: InvitationCode | None) -> Response:
    """根据邀请码真实状态返回明确文案，避免前端只能展示泛化失败原因。"""
    if invitation is None:
        message = "邀请码不存在。"
    elif invitation.effective_status == InvitationCode.Status.USED:
        message = "邀请码已经被使用。"
    elif invitation.effective_status == InvitationCode.Status.EXPIRED:
        message = "邀请码已经过期。"
    elif invitation.effective_status == InvitationCode.Status.REVOKED:
        message = "邀请码已经作废。"
    else:
        message = "邀请码不可用。"
    return api_error_response("invalid_invitation_code", message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["认证"],
        summary="用户登录",
        description="校验账号密码，成功后写入 HttpOnly `authToken` Cookie，并返回当前用户摘要。",
        request=LoginSerializer,
        responses={
            200: UserDataResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="账户或密码错误"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="用户不可登录"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="请求参数校验失败"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error(serializer)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = UserAccount.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            return api_error_response("invalid_credentials", "账户或密码错误。", status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return api_error_response("user_inactive", "用户不可登录。", status.HTTP_403_FORBIDDEN)

        user.mark_logged_in()
        response = Response({"data": UserSummarySerializer(user).data})
        response.set_cookie(
            settings.AUTH_COOKIE_NAME,
            issue_auth_token(user),
            max_age=settings.AUTH_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
        )
        return response


class LogoutView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["认证"],
        summary="用户登出",
        description="清理浏览器侧认证 Cookie。该接口需要携带有效认证 Cookie。",
        request=None,
        responses={
            204: OpenApiResponse(description="登出成功，无响应体"),
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
        },
    )
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.AUTH_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response


class AuthMeView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["认证"],
        summary="获取当前用户",
        description="根据认证 Cookie 返回当前登录用户摘要和权限编码。",
        responses={
            200: UserDataResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
        },
    )
    def get(self, request):
        return Response({"data": UserSummarySerializer(request.user).data})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["认证"],
        summary="邀请码注册",
        description="使用未过期且未使用的邀请码注册用户。注册成功不自动登录，不写入认证 Cookie。",
        request=RegisterSerializer,
        responses={
            201: UserDataResponseSerializer,
            409: OpenApiResponse(ApiErrorResponseSerializer, description="账号已存在"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="邀请码不可用、账号格式非法、密码不一致或密码不满足要求"),
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            field_level_codes = {"required", "blank", "null"}
            if has_serializer_error_code(serializer.errors, "password", field_level_codes) or has_serializer_error_code(
                serializer.errors,
                "confirm_password",
                field_level_codes,
            ):
                return validation_error(serializer)
            if "username" in serializer.errors:
                return api_error_response(
                    "invalid_username",
                    "账号只能包含字母、数字、下划线、短横线和点。",
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            if "confirm_password" in serializer.errors:
                return api_error_response("password_mismatch", "两次输入的密码不一致。", status.HTTP_422_UNPROCESSABLE_ENTITY)
            if "password" in serializer.errors:
                password = request.data.get("password", "")
                return api_error_response(
                    "weak_password",
                    build_password_requirement_message(str(password)),
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            return validation_error(serializer)

        username = serializer.validated_data["username"]
        if UserAccount.objects.filter(username=username).exists():
            return api_error_response("username_taken", "账号已存在。", status.HTTP_409_CONFLICT)

        invitation = InvitationCode.objects.select_for_update().filter(
            code_hash=InvitationCode.hash_code(serializer.validated_data["invitation_code"])
        ).first()
        if invitation is None or not invitation.can_register():
            return register_invitation_error(invitation)

        user = UserAccount.objects.create_user(
            username=username,
            display_name=serializer.validated_data.get("display_name", "") or username,
            password=serializer.validated_data["password"],
            role=invitation.role,
        )
        invitation.mark_used(user)
        return Response({"data": UserSummarySerializer(user).data}, status=status.HTTP_201_CREATED)


class UserListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["用户管理"],
        summary="分页查询用户",
        description="管理人员按角色分页查询用户列表。普通成员访问返回 `admin_required`。",
        parameters=[
            OpenApiParameter("role", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["admin", "member"]),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，从 1 开始"),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页条数，范围 1-100"),
        ],
        responses={
            200: UserListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="分页或筛选参数非法"),
        },
    )
    def get(self, request):
        forbidden = require_admin(request.user)
        if forbidden:
            return forbidden

        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination

        role = request.query_params.get("role")
        if role and role not in [UserAccount.Role.ADMIN, UserAccount.Role.MEMBER]:
            return api_error_response("validation_error", "角色筛选参数非法。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        queryset = UserAccount.objects.all()
        if role:
            queryset = queryset.filter(role=role)
        return paginated_response(queryset, UserSummarySerializer, page, per_page)


class InvitationListCreateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["邀请码"],
        summary="分页查询邀请码",
        description="管理人员按角色和状态分页查询邀请码。`unused` 会排除已过期记录，`expired` 会返回已过期未使用记录。",
        parameters=[
            OpenApiParameter("role", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["admin", "member"]),
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["unused", "used", "revoked", "expired"]),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，从 1 开始"),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页条数，范围 1-100"),
        ],
        responses={
            200: InvitationListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="分页或筛选参数非法"),
        },
    )
    def get(self, request):
        forbidden = require_admin(request.user)
        if forbidden:
            return forbidden

        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination

        role = request.query_params.get("role")
        status_filter = request.query_params.get("status")
        if role and role not in [UserAccount.Role.ADMIN, UserAccount.Role.MEMBER]:
            return api_error_response("validation_error", "角色筛选参数非法。", status.HTTP_422_UNPROCESSABLE_ENTITY)
        if status_filter and status_filter not in [choice.value for choice in InvitationCode.Status]:
            return api_error_response("validation_error", "状态筛选参数非法。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        queryset = InvitationCode.objects.select_related("created_by", "used_by", "revoked_by")
        if role:
            queryset = queryset.filter(role=role)
        if status_filter:
            if status_filter == InvitationCode.Status.EXPIRED:
                queryset = queryset.filter(status=InvitationCode.Status.UNUSED, expires_at__lt=timezone.now())
            elif status_filter == InvitationCode.Status.UNUSED:
                queryset = queryset.filter(status=InvitationCode.Status.UNUSED, expires_at__gte=timezone.now())
            else:
                queryset = queryset.filter(status=status_filter)
        return paginated_response(queryset, InvitationSummarySerializer, page, per_page)

    @extend_schema(
        tags=["邀请码"],
        summary="创建邀请码",
        description="管理人员创建一次性邀请码。明文邀请码只在创建响应中返回一次。",
        request=InvitationCreateSerializer,
        responses={
            201: InvitationCreateResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="请求参数校验失败"),
        },
    )
    def post(self, request):
        forbidden = require_admin(request.user)
        if forbidden:
            return forbidden

        serializer = InvitationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error(serializer)

        invitation, plain_code = InvitationCode.objects.create_plain_code(
            role=serializer.validated_data["role"],
            expires_at=serializer.validated_data.get("expires_at"),
            created_by=request.user,
        )
        data = InvitationSummarySerializer(invitation).data
        data["plain_code"] = plain_code
        return Response({"data": data}, status=status.HTTP_201_CREATED)


class InvitationRevokeView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["邀请码"],
        summary="作废邀请码",
        description="管理人员作废未使用且未过期的邀请码。已使用、已作废或已过期的邀请码不可作废。",
        request=None,
        parameters=[
            OpenApiParameter("invitation_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="邀请码记录 ID"),
        ],
        responses={
            200: InvitationDataResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="邀请码不存在"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="邀请码状态不允许作废"),
        },
    )
    def post(self, request, invitation_id: int):
        forbidden = require_admin(request.user)
        if forbidden:
            return forbidden

        invitation = InvitationCode.objects.filter(id=invitation_id).first()
        if invitation is None:
            return api_error_response("invitation_not_found", "邀请码不存在。", status.HTTP_404_NOT_FOUND)
        if invitation.status == InvitationCode.Status.USED:
            return api_error_response("invitation_already_used", "已使用的邀请码不可作废。", status.HTTP_409_CONFLICT)
        if invitation.effective_status != InvitationCode.Status.UNUSED:
            return api_error_response("invitation_not_revocable", "邀请码不可作废。", status.HTTP_409_CONFLICT)

        invitation.revoke(request.user)
        return Response({"data": InvitationSummarySerializer(invitation).data})
