from __future__ import annotations

from decimal import Decimal, InvalidOperation

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from common.exceptions import api_error_response
from common.pagination import paginated_response, parse_pagination
from common.serializers import ApiErrorResponseSerializer
from metrics.models import EnvironmentSnapshot, ModuleSnapshot, TestEnvironment
from metrics.serializers import (
    EnvironmentSummarySerializer,
    EnvironmentSummaryResponseSerializer,
    ModuleSnapshotListResponseSerializer,
    ModuleSnapshotSerializer,
    TestEnvironmentListResponseSerializer,
    TestEnvironmentSerializer,
)


SORT_FIELDS = {
    "pass_rate",
    "-pass_rate",
    "completed_at",
    "-completed_at",
    "failed_count",
    "-failed_count",
}


def validation_error(message: str = "请求参数校验失败。") -> Response:
    return api_error_response("validation_error", message, status.HTTP_422_UNPROCESSABLE_ENTITY)


def parse_environment_id(raw_value: str | None) -> int | Response:
    if raw_value is None:
        return validation_error("environment_id 为必填参数。")
    try:
        environment_id = int(raw_value)
    except ValueError:
        return validation_error("environment_id 必须为整数。")
    if environment_id < 1:
        return validation_error("environment_id 必须为正整数。")
    return environment_id


def parse_pass_rate_lte(raw_value: str | None) -> Decimal | Response | None:
    if raw_value in (None, ""):
        return None
    try:
        percent_value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return validation_error("通过率上限必须为 0-100 的数字。")
    if percent_value < 0 or percent_value > 100:
        return validation_error("通过率上限必须为 0-100。")
    return percent_value / Decimal("100")


def parse_sort(raw_value: str | None) -> list[str] | Response:
    if not raw_value:
        return ["pass_rate", "-completed_at", "id"]
    sort_fields = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not sort_fields or any(field not in SORT_FIELDS for field in sort_fields):
        return validation_error("排序字段非法。")
    return sort_fields + ["id"]


class TestEnvironmentListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询测试环境列表",
        description="登录用户查询可用测试环境列表。P2 默认只有模拟测试环境。",
        parameters=[
            OpenApiParameter("is_active", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="是否只查询启用环境"),
        ],
        responses={
            200: TestEnvironmentListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
        },
    )
    def get(self, request):
        queryset = TestEnvironment.objects.all()
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in {"1", "true", "yes"})
        return Response({"data": TestEnvironmentSerializer(queryset, many=True).data})


class EnvironmentSummaryView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询环境通过率汇总",
        description="登录用户查询指定测试环境的最新有效快照。无快照时返回空统计。",
        parameters=[
            OpenApiParameter("environment_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="测试环境 ID"),
        ],
        responses={
            200: EnvironmentSummaryResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="环境不存在"),
        },
    )
    def get(self, request, environment_id: int):
        environment = TestEnvironment.objects.filter(id=environment_id, is_active=True).first()
        if environment is None:
            return api_error_response("environment_not_found", "测试环境不存在。", status.HTTP_404_NOT_FOUND)

        snapshot = EnvironmentSnapshot.objects.filter(environment=environment).first()
        if snapshot is None:
            data = {
                "environment": TestEnvironmentSerializer(environment).data,
                "started_at": None,
                "finished_at": None,
                "duration_seconds": None,
                "total_count": 0,
                "failed_count": 0,
                "passed_count": 0,
                "skipped_count": 0,
                "pass_rate": Decimal("0.000000"),
                "actions": {"generate_report": True},
            }
            return Response({"data": EnvironmentSummarySerializer(data).data})

        data = {
            "environment": environment,
            "started_at": snapshot.started_at,
            "finished_at": snapshot.finished_at,
            "duration_seconds": snapshot.duration_seconds,
            "total_count": snapshot.total_count,
            "failed_count": snapshot.failed_count,
            "passed_count": snapshot.passed_count,
            "skipped_count": snapshot.skipped_count,
            "pass_rate": snapshot.pass_rate,
            "actions": {"generate_report": True},
        }
        return Response({"data": EnvironmentSummarySerializer(data).data})


class ModuleSnapshotListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="分页查询模块通过率快照",
        description="登录用户按环境分页查询模块最新只读快照，支持模块字段筛选和通过率/日期/失败数排序。",
        parameters=[
            OpenApiParameter("environment_id", OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="测试环境 ID"),
            OpenApiParameter("module_test", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模块测试人，模糊匹配"),
            OpenApiParameter("module_name", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模块名称，模糊匹配"),
            OpenApiParameter("package_name", OpenApiTypes.STR, OpenApiParameter.QUERY, description="用例包名，模糊匹配"),
            OpenApiParameter("pass_rate_lte", OpenApiTypes.NUMBER, OpenApiParameter.QUERY, description="通过率上限，百分比 0-100"),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，从 1 开始"),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页条数，范围 1-100"),
            OpenApiParameter("sort", OpenApiTypes.STR, OpenApiParameter.QUERY, description="排序字段，支持 pass_rate、completed_at、failed_count，可带 -"),
        ],
        responses={
            200: ModuleSnapshotListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="筛选、排序或分页参数非法"),
        },
    )
    def get(self, request):
        environment_id = parse_environment_id(request.query_params.get("environment_id"))
        if isinstance(environment_id, Response):
            return environment_id
        if not TestEnvironment.objects.filter(id=environment_id, is_active=True).exists():
            return validation_error("environment_id 无效。")

        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination

        pass_rate_lte = parse_pass_rate_lte(request.query_params.get("pass_rate_lte"))
        if isinstance(pass_rate_lte, Response):
            return pass_rate_lte

        sort_fields = parse_sort(request.query_params.get("sort"))
        if isinstance(sort_fields, Response):
            return sort_fields

        queryset = ModuleSnapshot.objects.select_related("module", "environment").filter(environment_id=environment_id)
        for param_name, lookup in [
            ("module_test", "module__module_test__icontains"),
            ("module_name", "module__module_name__icontains"),
            ("package_name", "module__package_name__icontains"),
        ]:
            value = request.query_params.get(param_name)
            if value:
                if len(value) > 128:
                    return validation_error(f"{param_name} 长度不能超过 128。")
                queryset = queryset.filter(**{lookup: value})
        if pass_rate_lte is not None:
            queryset = queryset.filter(pass_rate__lte=pass_rate_lte)
        queryset = queryset.order_by(*sort_fields)
        return paginated_response(queryset, ModuleSnapshotSerializer, page, per_page)
