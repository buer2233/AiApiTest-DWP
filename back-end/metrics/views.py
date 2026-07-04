from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CookieJWTAuthentication
from accounts.models import UserAccount
from common.exceptions import api_error_response
from common.pagination import parse_pagination
from common.serializers import ApiErrorResponseSerializer
from metrics.models import CaseStatusAudit, EnvironmentSnapshot, ModuleRunHistory, ModuleSnapshot, TestCaseResult, TestEnvironment
from metrics.serializers import (
    CaseResultListResponseSerializer,
    CaseResultSerializer,
    CaseStatusUpdateRequestSerializer,
    CaseStatusUpdateResponseSerializer,
    EnvironmentSummarySerializer,
    EnvironmentSummaryResponseSerializer,
    ModuleRunHistorySerializer,
    ModuleTrendResponseSerializer,
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
CASE_STATUSES = {"failed", "passed", "skipped"}




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


def paginated_response_with_context(queryset, serializer_class, page: int, per_page: int, context: dict) -> Response:
    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page
    serializer = serializer_class(queryset[start:end], many=True, context=context)
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


def calculate_pass_rate(total_count: int, failed_count: int) -> Decimal:
    if total_count <= 0:
        return Decimal("0.000000")
    return (Decimal(total_count - failed_count) / Decimal(total_count)).quantize(Decimal("0.000001"))


def status_delta(from_status: str, to_status: str) -> dict[str, int]:
    delta = {"failed_count": 0, "passed_count": 0, "skipped_count": 0}
    field_by_status = {
        TestCaseResult.DisplayStatus.FAILED: "failed_count",
        TestCaseResult.DisplayStatus.PASSED: "passed_count",
        TestCaseResult.DisplayStatus.SKIPPED: "skipped_count",
    }
    delta[field_by_status[from_status]] -= 1
    delta[field_by_status[to_status]] += 1
    return delta


def apply_snapshot_delta(snapshot, delta: dict[str, int]) -> None:
    # 状态修改只在展示状态间迁移，总数不变，失败数变化后按 P2 公式重算通过率。
    snapshot.failed_count += delta["failed_count"]
    snapshot.passed_count += delta["passed_count"]
    snapshot.skipped_count += delta["skipped_count"]
    snapshot.pass_rate = calculate_pass_rate(snapshot.total_count, snapshot.failed_count)
    snapshot.save(update_fields=["failed_count", "passed_count", "skipped_count", "pass_rate", "updated_at"])


def is_admin(user) -> bool:
    return getattr(user, "role", None) == UserAccount.Role.ADMIN


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
        return paginated_response_with_context(queryset, ModuleSnapshotSerializer, page, per_page, {})


class ModuleSnapshotCasesView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询模块用例详情",
        description="登录用户查询模块当前用例结果。默认筛选失败用例；管理人员可查看脱敏详情，普通成员仅看摘要。",
        parameters=[
            OpenApiParameter("snapshot_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="模块快照 ID"),
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["failed", "passed", "skipped"], description="展示状态，默认 failed"),
            OpenApiParameter("case_name", OpenApiTypes.STR, OpenApiParameter.QUERY, description="用例名模糊筛选，最多 256 字"),
            OpenApiParameter("node_id", OpenApiTypes.STR, OpenApiParameter.QUERY, description="pytest node id 模糊筛选，最多 1024 字"),
            OpenApiParameter("error_type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="错误类型筛选，最多 128 字"),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，从 1 开始"),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页条数，范围 1-100"),
        ],
        responses={
            200: CaseResultListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="模块快照不存在：module_snapshot_not_found"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="状态、筛选或分页参数非法：validation_error"),
        },
    )
    def get(self, request, snapshot_id: int):
        snapshot = (
            ModuleSnapshot.objects.select_related("environment", "module")
            .filter(id=snapshot_id, environment__is_active=True)
            .first()
        )
        if snapshot is None:
            return api_error_response("module_snapshot_not_found", "模块快照不存在。", status.HTTP_404_NOT_FOUND)

        display_status = request.query_params.get("status", TestCaseResult.DisplayStatus.FAILED)
        if display_status not in CASE_STATUSES:
            return validation_error("用例状态筛选非法。")

        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination

        queryset = TestCaseResult.objects.filter(
            module_snapshot=snapshot,
            is_current=True,
            display_status=display_status,
        )
        for param_name, max_length, lookup in [
            ("case_name", 256, "case_name__icontains"),
            ("node_id", 1024, "node_id__icontains"),
            ("error_type", 128, "error_type__icontains"),
        ]:
            value = request.query_params.get(param_name)
            if value:
                if len(value) > max_length:
                    return validation_error(f"{param_name} 长度超出限制。")
                queryset = queryset.filter(**{lookup: value})

        context = {
            "can_update_status": is_admin(request.user),
            "can_view_error_detail": is_admin(request.user),
        }
        queryset = queryset.order_by("display_status", "-occurred_at", "id")
        return paginated_response_with_context(queryset, CaseResultSerializer, page, per_page, context)


class CaseResultStatusUpdateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="管理人员修改用例状态",
        description="管理人员手动修改当前用例展示状态，写入状态审计并同步刷新模块和环境快照。",
        request=CaseStatusUpdateRequestSerializer,
        parameters=[
            OpenApiParameter("case_result_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="用例结果 ID"),
        ],
        responses={
            200: CaseStatusUpdateResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="用例结果不存在：case_result_not_found"),
            409: OpenApiResponse(
                ApiErrorResponseSerializer,
                description="用例状态未变化或已归档：case_status_unchanged / archived_case_result",
            ),
            422: OpenApiResponse(
                ApiErrorResponseSerializer,
                description="目标状态或修改原因非法：invalid_case_status / validation_error",
            ),
        },
    )
    @transaction.atomic
    def patch(self, request, case_result_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)

        case_result = (
            TestCaseResult.objects.select_for_update()
            .select_related("module_snapshot", "environment", "module")
            .filter(id=case_result_id)
            .first()
        )
        if case_result is None:
            return api_error_response("case_result_not_found", "用例结果不存在。", status.HTTP_404_NOT_FOUND)
        if not case_result.is_current or case_result.display_status == TestCaseResult.DisplayStatus.ARCHIVED:
            return api_error_response("archived_case_result", "已归档用例不可修改。", status.HTTP_409_CONFLICT)

        serializer = CaseStatusUpdateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            if "display_status" in serializer.errors:
                return api_error_response("invalid_case_status", "目标用例状态非法。", status.HTTP_422_UNPROCESSABLE_ENTITY)
            return validation_error("修改原因不能为空且不能超过 512 字。")

        target_status = serializer.validated_data["display_status"]
        reason = serializer.validated_data["reason"]
        if case_result.display_status == target_status:
            return api_error_response("case_status_unchanged", "用例状态未变化。", status.HTTP_409_CONFLICT)

        delta = status_delta(case_result.display_status, target_status)
        from_status = case_result.display_status
        case_result.display_status = target_status
        case_result.confirmation_result = reason[:128]
        case_result.save(update_fields=["display_status", "confirmation_result", "updated_at"])

        module_snapshot = ModuleSnapshot.objects.select_for_update().get(id=case_result.module_snapshot_id)
        apply_snapshot_delta(module_snapshot, delta)

        environment_snapshot = EnvironmentSnapshot.objects.select_for_update().filter(environment=case_result.environment).first()
        if environment_snapshot is not None:
            apply_snapshot_delta(environment_snapshot, delta)

        audit = CaseStatusAudit.objects.create(
            case_result=case_result,
            environment=case_result.environment,
            module=case_result.module,
            changed_by=request.user,
            from_status=from_status,
            to_status=target_status,
            reason=reason,
        )
        return Response(
            {
                "data": {
                    "case_result": {
                        "id": case_result.id,
                        "display_status": case_result.display_status,
                        "confirmation_result": case_result.confirmation_result,
                    },
                    "module_summary": {
                        "snapshot_id": module_snapshot.id,
                        "total_count": module_snapshot.total_count,
                        "failed_count": module_snapshot.failed_count,
                        "passed_count": module_snapshot.passed_count,
                        "skipped_count": module_snapshot.skipped_count,
                        "pass_rate": f"{module_snapshot.pass_rate:.6f}",
                    },
                    "environment_summary": {
                        "environment_id": case_result.environment_id,
                        "total_count": environment_snapshot.total_count if environment_snapshot else 0,
                        "failed_count": environment_snapshot.failed_count if environment_snapshot else 0,
                        "pass_rate": f"{environment_snapshot.pass_rate:.6f}" if environment_snapshot else "0.000000",
                    },
                    "audit_id": audit.id,
                }
            }
        )


class ModuleSnapshotTrendView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询模块通过率趋势",
        description="登录用户查询指定模块近 7 天或 30 天通过率趋势。days 不是 7 或 30 时返回校验错误。",
        parameters=[
            OpenApiParameter("snapshot_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="模块快照 ID"),
            OpenApiParameter("days", OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, enum=[7, 30], description="统计窗口，只支持 7 或 30"),
        ],
        responses={
            200: ModuleTrendResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="模块快照不存在：module_snapshot_not_found"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="days 不是 7 或 30：validation_error"),
        },
    )
    def get(self, request, snapshot_id: int):
        snapshot = (
            ModuleSnapshot.objects.select_related("environment", "module")
            .filter(id=snapshot_id, environment__is_active=True)
            .first()
        )
        if snapshot is None:
            return api_error_response("module_snapshot_not_found", "模块快照不存在。", status.HTTP_404_NOT_FOUND)
        try:
            days = int(request.query_params.get("days", ""))
        except ValueError:
            return validation_error("days 只能为 7 或 30。")
        if days not in {7, 30}:
            return validation_error("days 只能为 7 或 30。")

        window_end = snapshot.completed_at.date() if snapshot.completed_at else timezone.localdate()
        window_start = window_end - timezone.timedelta(days=days - 1)
        series = (
            ModuleRunHistory.objects.filter(
                environment=snapshot.environment,
                module=snapshot.module,
                run_date__gte=window_start,
                run_date__lte=window_end,
            )
            .order_by("run_date", "id")[:30]
        )
        data = {
            "module": {
                "snapshot_id": snapshot.id,
                "module_name": snapshot.module.module_name,
                "package_name": snapshot.module.package_name,
                "environment_name": snapshot.environment.env_name,
            },
            "days": days,
            "series": ModuleRunHistorySerializer(series, many=True).data,
        }
        return Response({"data": data})
