from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.exceptions import api_error_response
from accounts.models import InvitationCode, UserAccount
from accounts.serializers import (
    InvitationCreateSerializer,
    InvitationSummarySerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSummarySerializer,
)
from accounts.tokens import issue_auth_token


def validation_error(serializer) -> Response:
    return api_error_response(
        "validation_error",
        "请求参数校验失败。",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=[serializer.errors],
    )


def require_admin(user: UserAccount) -> Response | None:
    if user.role != UserAccount.Role.ADMIN:
        return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
    return None


def parse_pagination(request) -> tuple[int, int] | Response:
    try:
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 20))
    except ValueError:
        return api_error_response("validation_error", "分页参数必须为整数。", status.HTTP_422_UNPROCESSABLE_ENTITY)
    if page < 1 or per_page < 1 or per_page > 100:
        return api_error_response("validation_error", "分页参数超出允许范围。", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return page, per_page


def paginated_response(queryset, serializer_class, page: int, per_page: int) -> Response:
    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page
    serializer = serializer_class(queryset[start:end], many=True)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return Response(
        {
            "data": serializer.data,
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            },
        }
    )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error(serializer)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = UserAccount.objects.filter(username=username).first()
        if user is None or not user.check_password(password):
            return api_error_response("invalid_credentials", "账号或密码错误。", status.HTTP_401_UNAUTHORIZED)
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
            samesite="Lax",
            path="/",
        )
        return response


class LogoutView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/", samesite="Lax")
        return response


class AuthMeView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def get(self, request):
        return Response({"data": UserSummarySerializer(request.user).data})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            if "password" in serializer.errors:
                return api_error_response("weak_password", "密码不满足复杂度要求。", status.HTTP_422_UNPROCESSABLE_ENTITY)
            if "confirm_password" in serializer.errors:
                return api_error_response("password_mismatch", "两次输入的密码不一致。", status.HTTP_422_UNPROCESSABLE_ENTITY)
            return validation_error(serializer)

        username = serializer.validated_data["username"]
        if UserAccount.objects.filter(username=username).exists():
            return api_error_response("username_taken", "账号已存在。", status.HTTP_409_CONFLICT)

        invitation = InvitationCode.objects.select_for_update().filter(
            code_hash=InvitationCode.hash_code(serializer.validated_data["invitation_code"])
        ).first()
        if invitation is None or not invitation.can_register():
            return api_error_response(
                "invalid_invitation_code",
                "邀请码不可用。",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

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
