from __future__ import annotations

import logging
import os
import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Max, Sum
from django.db import DatabaseError, IntegrityError, transaction
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
from metrics.jenkins_service import (
    JenkinsBuildMatchError,
    JenkinsServiceError,
    cancel_jenkins_task,
    discover_jenkins_builds as discover_jenkins_builds_from_jenkins,
    fetch_jenkins_task_result,
    trigger_jenkins_build,
)
from metrics.module_metadata import build_filter_options_from_package_module_yaml
from metrics.models import (
    CaseStatusAudit,
    EnvironmentCatalogState,
    EnvironmentCatalogSyncAttempt,
    EnvironmentSnapshot,
    JenkinsJobBinding,
    JenkinsTask,
    ModuleExecutionLock,
    ModuleRunHistory,
    ModuleSnapshot,
    TestCaseResult,
    TestEnvironment,
    TestModule,
    TestRun,
    normalize_environment_base_url,
)
from metrics.serializers import (
    CaseResultListResponseSerializer,
    CaseResultSerializer,
    CaseStatusUpdateRequestSerializer,
    CaseStatusUpdateResponseSerializer,
    EnvironmentCatalogEnvironmentSerializer,
    EnvironmentCatalogListResponseSerializer,
    EnvironmentCatalogStateSerializer,
    EnvironmentCatalogSyncAttemptResponseSerializer,
    EnvironmentCatalogSyncAttemptSerializer,
    EnvironmentCatalogWriteEnvelopeSerializer,
    EnvironmentSummarySerializer,
    EnvironmentSummaryResponseSerializer,
    JenkinsTaskListResponseSerializer,
    JenkinsTaskBulkSyncRequestSerializer,
    JenkinsTaskBulkSyncResponseSerializer,
    JenkinsTaskResponseSerializer,
    JenkinsTaskSerializer,
    ModuleSnapshotFilterOptionsResponseSerializer,
    ModuleRunHistorySerializer,
    ModuleTrendResponseSerializer,
    ModuleSnapshotListResponseSerializer,
    ModuleSnapshotSerializer,
    TestEnvironmentCreateRequestSerializer,
    TestEnvironmentUpdateRequestSerializer,
    TestEnvironmentSerializer,
)
from metrics import environment_catalog as catalog_service


SORT_FIELDS = {
    "pass_rate",
    "-pass_rate",
    "completed_at",
    "-completed_at",
    "failed_count",
    "-failed_count",
}
CASE_STATUSES = {"failed", "passed", "skipped"}
logger = logging.getLogger(__name__)




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


def parse_multi_select_values(param_name: str, raw_value: str | None) -> list[str] | Response | None:
    if raw_value in (None, ""):
        return None
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not values:
        return None
    if len(values) > 50:
        return validation_error(f"{param_name} 最多支持 50 个筛选值。")
    if any(len(value) > 128 for value in values):
        return validation_error(f"{param_name} 单个筛选值长度不能超过 128。")
    return values


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


LOCKED_MESSAGE = "本模块已经有真正执行的重试!"
TERMINAL_TASK_STATUSES = {
    TestRun.Status.SUCCESS,
    TestRun.Status.TEST_FAILED,
    TestRun.Status.FAILED,
    TestRun.Status.CANCELED,
}
ACTIVE_TASK_STATUSES = {
    TestRun.Status.QUEUED,
    TestRun.Status.RUNNING,
    TestRun.Status.CANCELING,
}
RERUN_TASK_TYPES = {
    TestRun.RunType.FAILED_RERUN,
    TestRun.RunType.MODULE_RERUN,
}
STALE_ACTIVE_TASK_AGE = timedelta(hours=2)


def get_active_snapshot(snapshot_id: int) -> ModuleSnapshot | None:
    return (
        ModuleSnapshot.objects.select_related("environment", "module")
        .filter(id=snapshot_id, environment__is_active=True)
        .first()
    )


def get_job_binding(snapshot: ModuleSnapshot, task_type: str) -> JenkinsJobBinding | None:
    return JenkinsJobBinding.objects.filter(
        environment=snapshot.environment,
        module=snapshot.module,
        task_type=task_type,
        is_active=True,
    ).first()


def active_lock_exists(snapshot: ModuleSnapshot) -> bool:
    return ModuleExecutionLock.objects.filter(
        environment=snapshot.environment,
        module=snapshot.module,
        status=ModuleExecutionLock.Status.ACTIVE,
    ).exists()


def active_rerun_task_exists(snapshot: ModuleSnapshot) -> bool:
    return JenkinsTask.objects.filter(
        environment=snapshot.environment,
        module=snapshot.module,
        task_type__in=RERUN_TASK_TYPES,
        status__in=ACTIVE_TASK_STATUSES,
    ).exists()


def module_execution_is_busy(snapshot: ModuleSnapshot) -> bool:
    return active_lock_exists(snapshot) or active_rerun_task_exists(snapshot)


def is_jenkins_task_not_found_error(exc: JenkinsServiceError) -> bool:
    message = str(exc).lower()
    return "http error 404" in message or "not found" in message


def mark_jenkins_task_missing(task: JenkinsTask, reason: str) -> JenkinsTask:
    """Jenkins 已找不到任务时释放本地互斥锁，避免历史 queued 任务长期阻塞重试。"""
    with transaction.atomic():
        locked_task = JenkinsTask.objects.select_for_update().select_related("run").get(id=task.id)
        if locked_task.status in TERMINAL_TASK_STATUSES:
            release_task_lock(locked_task, "task already terminal")
            return locked_task
        locked_task.status = TestRun.Status.FAILED
        locked_task.error_summary = f"Jenkins task not found while refreshing module lock: {reason}"
        locked_task.finished_at = timezone.now()
        locked_task.last_synced_at = locked_task.finished_at
        locked_task.save(update_fields=["status", "error_summary", "finished_at", "last_synced_at", "updated_at"])
        if locked_task.run:
            locked_task.run.status = TestRun.Status.FAILED
            locked_task.run.finished_at = locked_task.finished_at
            locked_task.run.save(update_fields=["status", "finished_at", "updated_at"])
        release_task_lock(locked_task, "jenkins task not found")
        return locked_task


def expire_stale_jenkins_task(task: JenkinsTask, reason: str) -> JenkinsTask:
    """本地任务超过最大保留时长仍未终结时过期锁，防止残留状态永久阻塞。"""
    with transaction.atomic():
        locked_task = JenkinsTask.objects.select_for_update().select_related("run").get(id=task.id)
        if locked_task.status in TERMINAL_TASK_STATUSES:
            release_task_lock(locked_task, "task already terminal")
            return locked_task
        locked_task.status = TestRun.Status.FAILED
        locked_task.error_summary = f"Local Jenkins task lock expired: {reason}"
        locked_task.finished_at = timezone.now()
        locked_task.last_synced_at = locked_task.finished_at
        locked_task.save(update_fields=["status", "error_summary", "finished_at", "last_synced_at", "updated_at"])
        if locked_task.run:
            locked_task.run.status = TestRun.Status.FAILED
            locked_task.run.finished_at = locked_task.finished_at
            locked_task.run.save(update_fields=["status", "finished_at", "updated_at"])
        locks = ModuleExecutionLock.objects.select_for_update().filter(
            task=locked_task,
            status=ModuleExecutionLock.Status.ACTIVE,
        )
        for lock in locks:
            lock.status = ModuleExecutionLock.Status.EXPIRED
            lock.released_at = timezone.now()
            lock.release_reason = "local active task expired"
            lock.save(update_fields=["status", "active_lock_key", "released_at", "release_reason", "updated_at"])
        return locked_task


def jenkins_task_is_stale(task: JenkinsTask) -> bool:
    return task.created_at <= timezone.now() - STALE_ACTIVE_TASK_AGE


def refresh_module_execution_state(snapshot: ModuleSnapshot) -> None:
    """触发新任务前刷新本模块运行状态，只在 Jenkins 明确不存在任务时释放锁。"""
    active_locks = ModuleExecutionLock.objects.select_related("task").filter(
        environment=snapshot.environment,
        module=snapshot.module,
        status=ModuleExecutionLock.Status.ACTIVE,
    )
    for lock in active_locks:
        if lock.task.status in TERMINAL_TASK_STATUSES:
            with transaction.atomic():
                release_task_lock(lock.task, "terminal task cleanup")

    active_tasks = JenkinsTask.objects.filter(
        environment=snapshot.environment,
        module=snapshot.module,
        task_type__in=RERUN_TASK_TYPES,
        status__in=ACTIVE_TASK_STATUSES,
    ).order_by("created_at", "id")
    for task in active_tasks:
        try:
            result = fetch_jenkins_task_result(task)
        except JenkinsServiceError as exc:
            if is_jenkins_task_not_found_error(exc):
                mark_jenkins_task_missing(task, str(exc))
            continue
        if result.get("queue_pending") and jenkins_task_is_stale(task):
            expire_stale_jenkins_task(task, f"status={task.status}, task_id={task.id}")
            continue
        sync_task_with_result(task, result)


def jenkins_task_response(task: JenkinsTask, request, response_status: int = status.HTTP_200_OK) -> Response:
    return Response({"data": JenkinsTaskSerializer(task, context={"request": request}).data}, status=response_status)


def record_jenkins_build_match_error(task: JenkinsTask, exc: JenkinsBuildMatchError) -> JenkinsTask:
    """记录构建匹配歧义，但不推进任务、TestRun 或互斥锁状态。"""
    with transaction.atomic():
        locked_task = JenkinsTask.objects.select_for_update().get(id=task.id)
        locked_task.error_summary = str(exc)
        locked_task.last_synced_at = timezone.now()
        locked_task.save(update_fields=["error_summary", "last_synced_at", "updated_at"])
        return locked_task


def create_queued_jenkins_task(
    *,
    snapshot: ModuleSnapshot,
    task_type: str,
    triggered_by,
    binding: JenkinsJobBinding,
    parameters: dict[str, str],
    requested_nodeids: list[str] | None = None,
) -> JenkinsTask | Response:
    refresh_module_execution_state(snapshot)
    if module_execution_is_busy(snapshot):
        return api_error_response("module_execution_locked", LOCKED_MESSAGE, status.HTTP_409_CONFLICT)

    try:
        with transaction.atomic():
            run = TestRun.objects.create(
                run_key=f"{task_type}-{snapshot.environment_id}-{snapshot.module_id}-{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
                run_type=task_type,
                environment=snapshot.environment,
                module=snapshot.module,
                status=TestRun.Status.QUEUED,
            )
            task = JenkinsTask.objects.create(
                run=run,
                environment=snapshot.environment,
                module=snapshot.module,
                task_type=task_type,
                trigger_source=JenkinsTask.TriggerSource.PLATFORM_USER,
                triggered_by=triggered_by,
                job_full_name=binding.job_full_name,
                status=TestRun.Status.QUEUED,
                requested_nodeids_json=requested_nodeids or [],
            )
            lock = ModuleExecutionLock.objects.create(
                environment=snapshot.environment,
                module=snapshot.module,
                task=task,
                lock_type="module_execution",
                status=ModuleExecutionLock.Status.ACTIVE,
                locked_at=timezone.now(),
            )
            try:
                build_parameters = {**parameters, "RUN_ID": run.run_key}
                queued = trigger_jenkins_build(job_full_name=binding.job_full_name, parameters=build_parameters)
            except JenkinsServiceError as exc:
                lock.status = ModuleExecutionLock.Status.RELEASED
                lock.released_at = timezone.now()
                lock.release_reason = "jenkins trigger failed"
                lock.save(update_fields=["status", "active_lock_key", "released_at", "release_reason", "updated_at"])
                task.status = TestRun.Status.FAILED
                task.error_summary = str(exc)
                task.finished_at = timezone.now()
                task.save(update_fields=["status", "error_summary", "finished_at", "updated_at"])
                run.status = TestRun.Status.FAILED
                run.finished_at = task.finished_at
                run.save(update_fields=["status", "finished_at", "updated_at"])
                raise RuntimeError(str(exc)) from exc
            task.queue_id = queued.get("queue_id") or None
            task.jenkins_queue_url = queued.get("queue_url", "")
            task.save(update_fields=["queue_id", "jenkins_queue_url", "updated_at"])
            return task
    except IntegrityError:
        return api_error_response("module_execution_locked", LOCKED_MESSAGE, status.HTTP_409_CONFLICT)
    except RuntimeError as exc:
        return api_error_response("jenkins_unavailable", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)


def release_task_lock(task: JenkinsTask, reason: str) -> None:
    locks = ModuleExecutionLock.objects.select_for_update().filter(
        task=task,
        status=ModuleExecutionLock.Status.ACTIVE,
    )
    for lock in locks:
        lock.status = ModuleExecutionLock.Status.RELEASED
        lock.released_at = timezone.now()
        lock.release_reason = reason
        lock.save(update_fields=["status", "active_lock_key", "released_at", "release_reason", "updated_at"])


def apply_failed_rerun_summary(task: JenkinsTask, failed_nodeids: list[str]) -> None:
    retried_nodeids = set(task.requested_nodeids_json or [])
    still_failed = set(failed_nodeids or [])
    passed_nodeids = retried_nodeids - still_failed
    if not passed_nodeids:
        return

    cases = TestCaseResult.objects.select_for_update().filter(
        environment=task.environment,
        module=task.module,
        is_current=True,
        display_status=TestCaseResult.DisplayStatus.FAILED,
        node_id__in=passed_nodeids,
    )
    changed = 0
    for case in cases:
        case.display_status = TestCaseResult.DisplayStatus.PASSED
        case.execution_status = TestCaseResult.ExecutionStatus.PASSED
        case.confirmation_result = "失败重试通过"
        case.save(update_fields=["display_status", "execution_status", "confirmation_result", "updated_at"])
        changed += 1
    if changed == 0:
        return

    snapshot = ModuleSnapshot.objects.select_for_update().get(environment=task.environment, module=task.module)
    snapshot.failed_count = max(snapshot.failed_count - changed, 0)
    snapshot.passed_count += changed
    snapshot.pass_rate = calculate_pass_rate(snapshot.total_count, snapshot.failed_count)
    # 失败重试不更新 completed_at 和 duration_seconds。
    snapshot.save(update_fields=["failed_count", "passed_count", "pass_rate", "updated_at"])
    environment_snapshot = EnvironmentSnapshot.objects.select_for_update().filter(environment=task.environment).first()
    if environment_snapshot:
        environment_snapshot.failed_count = max(environment_snapshot.failed_count - changed, 0)
        environment_snapshot.passed_count += changed
        environment_snapshot.pass_rate = calculate_pass_rate(environment_snapshot.total_count, environment_snapshot.failed_count)
        environment_snapshot.save(update_fields=["failed_count", "passed_count", "pass_rate", "updated_at"])


def case_name_from_nodeid(node_id: str) -> str:
    """从 pytest node id 中提取可读用例名，Jenkins summary 当前只提供 node id。"""
    return node_id.rsplit("::", 1)[-1] if "::" in node_id else node_id.rsplit("/", 1)[-1]


def refresh_environment_snapshot(environment) -> None:
    """按所有模块快照重算环境汇总，避免单模块全量后环境统计滞后。"""
    totals = ModuleSnapshot.objects.filter(environment=environment).aggregate(
        total_count=Sum("total_count"),
        failed_count=Sum("failed_count"),
        passed_count=Sum("passed_count"),
        skipped_count=Sum("skipped_count"),
        finished_at=Max("completed_at"),
    )
    snapshot = EnvironmentSnapshot.objects.select_for_update().filter(environment=environment).first()
    if snapshot is None:
        return
    snapshot.total_count = int(totals["total_count"] or 0)
    snapshot.failed_count = int(totals["failed_count"] or 0)
    snapshot.passed_count = int(totals["passed_count"] or 0)
    snapshot.skipped_count = int(totals["skipped_count"] or 0)
    snapshot.pass_rate = calculate_pass_rate(snapshot.total_count, snapshot.failed_count)
    snapshot.finished_at = totals["finished_at"]
    snapshot.save(
        update_fields=[
            "total_count",
            "failed_count",
            "passed_count",
            "skipped_count",
            "pass_rate",
            "finished_at",
            "updated_at",
        ]
    )


def normalize_module_case_results(summary: dict, total_count: int) -> tuple[list[dict], str | None]:
    """校验模块全量用例明细；契约不完整时返回警告并禁止替换旧结果。"""
    raw_case_results = summary.get("case_results")
    if not isinstance(raw_case_results, list):
        return [], "Jenkins summary case_results is missing or invalid; current case details were preserved."

    normalized_by_node_id: dict[str, dict] = {}
    allowed_statuses = {choice for choice, _ in TestCaseResult.ExecutionStatus.choices}
    for raw_case in raw_case_results:
        if not isinstance(raw_case, dict):
            return [], "Jenkins summary case_results contains a non-object item; current case details were preserved."
        node_id = str(raw_case.get("node_id") or "").strip()
        execution_status = str(raw_case.get("execution_status") or "").strip()
        if not node_id or len(node_id) > 1024 or execution_status not in allowed_statuses:
            return [], "Jenkins summary case_results contains an invalid node id or status; current case details were preserved."
        if node_id in normalized_by_node_id:
            return [], "Jenkins summary case_results contains duplicate node ids; current case details were preserved."
        normalized_by_node_id[node_id] = {
            "node_id": node_id,
            "case_name": str(raw_case.get("case_name") or case_name_from_nodeid(node_id))[:256],
            "execution_status": execution_status,
            "error_type": str(raw_case.get("error_type") or "")[:128],
            "error_message_summary": str(raw_case.get("error_message_summary") or "")[:512],
        }

    normalized = list(normalized_by_node_id.values())
    if len(normalized) != total_count:
        return [], "Jenkins summary case_results count does not match total_count; current case details were preserved."
    status_counts = {
        "failed_count": sum(
            item["execution_status"] in {TestCaseResult.ExecutionStatus.FAILED, TestCaseResult.ExecutionStatus.ERROR}
            for item in normalized
        ),
        "passed_count": sum(item["execution_status"] == TestCaseResult.ExecutionStatus.PASSED for item in normalized),
        "skipped_count": sum(item["execution_status"] == TestCaseResult.ExecutionStatus.SKIPPED for item in normalized),
    }
    for field_name, actual_count in status_counts.items():
        expected_count = int(summary.get(field_name, 0) or 0)
        if actual_count != expected_count:
            return [], f"Jenkins summary {field_name} does not match case_results count; current case details were preserved."
    return normalized, None


def normalize_module_summary(summary: dict) -> tuple[dict | None, str | None]:
    """先校验模块统计和完整明细，避免降级路径产生部分数据更新。"""
    if not isinstance(summary, dict):
        return None, "Jenkins summary is invalid; current module metrics were preserved."

    normalized_counts: dict[str, int] = {}
    for field_name in ("total_count", "failed_count", "skipped_count"):
        raw_value = summary.get(field_name, 0 if field_name == "skipped_count" else None)
        try:
            if raw_value is None or isinstance(raw_value, bool):
                raise ValueError
            parsed_value = int(raw_value)
            if parsed_value < 0 or (isinstance(raw_value, float) and not raw_value.is_integer()):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            return None, f"Jenkins summary {field_name} is invalid; current module metrics were preserved."
        normalized_counts[field_name] = parsed_value

    default_passed = (
        normalized_counts["total_count"]
        - normalized_counts["failed_count"]
        - normalized_counts["skipped_count"]
    )
    raw_passed = summary.get("passed_count", default_passed)
    try:
        if isinstance(raw_passed, bool):
            raise ValueError
        passed_count = int(raw_passed)
        if passed_count < 0 or (isinstance(raw_passed, float) and not raw_passed.is_integer()):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        return None, "Jenkins summary passed_count is invalid; current module metrics were preserved."
    normalized_counts["passed_count"] = passed_count

    if sum(normalized_counts[field] for field in ("failed_count", "passed_count", "skipped_count")) != normalized_counts[
        "total_count"
    ]:
        return None, "Jenkins summary status counts do not match total_count; current module metrics were preserved."

    raw_duration = summary.get("duration_seconds")
    duration_seconds = None
    if raw_duration is not None:
        try:
            duration_seconds = Decimal(str(raw_duration))
            if not duration_seconds.is_finite() or duration_seconds < 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            return None, "Jenkins summary duration_seconds is invalid; current module metrics were preserved."

    normalized_summary = {**summary, **normalized_counts}
    case_results, warning = normalize_module_case_results(normalized_summary, normalized_counts["total_count"])
    if warning:
        return None, warning
    return {
        **normalized_counts,
        "duration_seconds": duration_seconds,
        "case_results": case_results,
    }, None


def apply_module_summary(task: JenkinsTask, summary: dict, *, module: TestModule | None = None) -> str | None:
    if task.task_type not in {TestRun.RunType.MODULE_RERUN, TestRun.RunType.DAILY_FULL}:
        return None
    normalized_summary, case_sync_warning = normalize_module_summary(summary)
    if case_sync_warning:
        return case_sync_warning

    total_count = normalized_summary["total_count"]
    failed_count = normalized_summary["failed_count"]
    passed_count = normalized_summary["passed_count"]
    skipped_count = normalized_summary["skipped_count"]
    case_results = normalized_summary["case_results"]
    completed_at = task.finished_at or timezone.now()
    duration_seconds = normalized_summary["duration_seconds"]
    resolved_module = module or task.module
    if resolved_module is None:
        return "Jenkins Daily parent summary is missing module context; current module metrics were preserved."
    snapshot = ModuleSnapshot.objects.select_for_update().get(environment=task.environment, module=resolved_module)
    history_duration = Decimal(str(duration_seconds)) if duration_seconds is not None else None
    history_pass_rate = calculate_pass_rate(total_count, failed_count)
    ModuleRunHistory.objects.update_or_create(
        environment=task.environment,
        module=resolved_module,
        source_run=task.run,
        run_date=timezone.localtime(completed_at).date(),
        run_type=task.task_type,
        defaults={
            "completed_at": completed_at,
            "duration_seconds": history_duration,
            "total_count": total_count,
            "failed_count": failed_count,
            "passed_count": passed_count,
            "skipped_count": skipped_count,
            "pass_rate": history_pass_rate,
        },
    )
    if snapshot.completed_at and completed_at < snapshot.completed_at:
        return None

    snapshot.total_count = total_count
    snapshot.failed_count = failed_count
    snapshot.passed_count = passed_count
    snapshot.skipped_count = skipped_count
    snapshot.pass_rate = calculate_pass_rate(snapshot.total_count, snapshot.failed_count)
    snapshot.completed_at = completed_at
    snapshot.duration_seconds = Decimal(str(duration_seconds)) if duration_seconds is not None else snapshot.duration_seconds
    snapshot.latest_run = task.run
    snapshot.save(
        update_fields=[
            "total_count",
            "failed_count",
            "passed_count",
            "skipped_count",
            "pass_rate",
            "completed_at",
            "duration_seconds",
            "latest_run",
            "updated_at",
        ]
    )
    TestCaseResult.objects.select_for_update().filter(
        environment=task.environment,
        module=resolved_module,
        is_current=True,
    ).update(
        is_current=False,
        current_node_key=None,
        display_status=TestCaseResult.DisplayStatus.ARCHIVED,
        confirmation_result="全量执行归档",
        updated_at=timezone.now(),
    )
    for case_result in case_results:
        execution_status = case_result["execution_status"]
        display_status = (
            TestCaseResult.DisplayStatus.FAILED
            if execution_status in {TestCaseResult.ExecutionStatus.FAILED, TestCaseResult.ExecutionStatus.ERROR}
            else execution_status
        )
        TestCaseResult.objects.create(
            environment=task.environment,
            module=resolved_module,
            module_snapshot=snapshot,
            source_run=task.run,
            node_id=case_result["node_id"],
            case_name=case_result["case_name"],
            case_summary="Jenkins 模块执行同步",
            execution_status=execution_status,
            display_status=display_status,
            error_type=case_result["error_type"],
            error_message_summary=case_result["error_message_summary"],
            confirmation_result="模块执行同步",
            occurred_at=completed_at,
        )
    refresh_environment_snapshot(task.environment)
    return None


class DailyParentEnvironmentError(RuntimeError):
    """父构建未提供可精确匹配的环境时，禁止猜测并创建平台任务。"""


def apply_daily_parent_summary(task: JenkinsTask, summary: dict) -> str | None:
    """把 Daily 父摘要按模块投影，单模块异常不回滚其他模块。"""
    if task.module_id is not None or task.environment_id is None:
        return "Jenkins Daily parent context is invalid; current module metrics were preserved."
    module_details = summary.get("modules")
    if not isinstance(module_details, list) or not module_details:
        return "Jenkins Daily parent summary modules is missing or invalid; current module metrics were preserved."
    warnings: list[str] = []
    if summary.get("module_count") != len(module_details):
        warnings.append("Jenkins Daily parent summary module_count is invalid; current module metrics were preserved.")

    modules = {
        module.package_name: module for module in TestModule.objects.filter(is_active=True).order_by("id")
    }
    received_keys: set[str] = set()
    for detail in module_details:
        if not isinstance(detail, dict):
            warnings.append("Jenkins Daily parent summary contains an invalid module detail; current module metrics were preserved.")
            continue
        module_key = detail.get("module_key")
        if not isinstance(module_key, str) or not module_key:
            warnings.append("Jenkins Daily parent summary contains a module with an invalid key; current module metrics were preserved.")
            continue
        if module_key in received_keys:
            warnings.append(f"{module_key}: duplicate module detail was ignored; current module metrics were preserved.")
            continue
        received_keys.add(module_key)
        module = modules.get(module_key)
        if module is None:
            warnings.append(f"{module_key}: unknown module detail was ignored; current module metrics were preserved.")
            continue
        try:
            # 每个模块使用保存点，单模块数据库异常不影响已成功的模块投影。
            with transaction.atomic():
                warning = apply_module_summary(task, detail, module=module)
        except (ModuleSnapshot.DoesNotExist, DatabaseError):
            warnings.append(f"{module_key}: module projection failed; current module metrics were preserved.")
            continue
        if warning:
            warnings.append(f"{module_key}: {warning}")

    if received_keys != set(modules):
        warnings.append("Jenkins Daily parent summary is missing module details; current module metrics were preserved.")
    return "; ".join(warnings) if warnings else None


def sync_task_with_result(task: JenkinsTask, result: dict) -> JenkinsTask:
    with transaction.atomic():
        task = JenkinsTask.objects.select_for_update().select_related("run").get(id=task.id)
        if task.status in TERMINAL_TASK_STATUSES:
            task.last_synced_at = timezone.now()
            task.save(update_fields=["last_synced_at", "updated_at"])
            return task

        if result.get("queue_pending"):
            task.last_synced_at = timezone.now()
            task.save(update_fields=["last_synced_at", "updated_at"])
            return task

        identity_update_fields: list[str] = []
        if result.get("build_number") and result["build_number"] != task.build_number:
            task.build_number = result["build_number"]
            identity_update_fields.append("build_number")
        if result.get("jenkins_build_url") and result["jenkins_build_url"] != task.jenkins_build_url:
            task.jenkins_build_url = result["jenkins_build_url"]
            identity_update_fields.append("jenkins_build_url")
        if result.get("started_at") and result["started_at"] != task.started_at:
            task.started_at = result["started_at"]
            identity_update_fields.append("started_at")

        if result.get("building"):
            update_fields = ["status", "last_synced_at", "updated_at", *identity_update_fields]
            task.status = TestRun.Status.RUNNING
            task.last_synced_at = timezone.now()
            if task.run:
                task.run.status = TestRun.Status.RUNNING
                task.run.started_at = task.started_at
                task.run.save(update_fields=["status", "started_at", "updated_at"])
            task.save(update_fields=sorted(set(update_fields)))
            return task

        if identity_update_fields and not any(
            key in result for key in ("summary", "jenkins_result", "canceled", "finished_at")
        ):
            task.status = TestRun.Status.RUNNING
            if task.run:
                task.run.status = TestRun.Status.RUNNING
                task.run.started_at = task.started_at
                task.run.save(update_fields=["status", "started_at", "updated_at"])
            task.last_synced_at = timezone.now()
            task.save(update_fields=sorted(set([*identity_update_fields, "status", "last_synced_at", "updated_at"])))
            return task

        raw_summary = result.get("summary")
        summary = raw_summary if isinstance(raw_summary, dict) else None
        failed_nodeids = list(result.get("failed_nodeids") or (summary or {}).get("failed_nodeids") or [])
        task.jenkins_result = result.get("jenkins_result") or task.jenkins_result
        task.summary_json = raw_summary
        task.failed_nodeids_json = failed_nodeids
        task.artifact_base_url = result.get("artifact_base_url", task.artifact_base_url)
        task.summary_artifact_url = result.get("summary_artifact_url", task.summary_artifact_url)
        task.failed_nodeids_artifact_url = result.get("failed_nodeids_artifact_url", task.failed_nodeids_artifact_url)
        task.allure_report_url = result.get("allure_report_url", task.allure_report_url)
        task.error_summary = result.get("error_summary", task.error_summary)
        task.finished_at = result.get("finished_at")
        if task.finished_at is None:
            task.finished_at = timezone.now()
            logger.warning(
                "Jenkins completion time unavailable; using sync time fallback: task_id=%s",
                task.id,
            )
        task.last_synced_at = timezone.now()

        if result.get("canceled") or task.jenkins_result == "ABORTED":
            task.status = TestRun.Status.CANCELED
        elif raw_summary is not None and summary is None:
            task.status = TestRun.Status.FAILED
            task.error_summary = "Jenkins summary artifact is invalid."
        elif not summary:
            task.status = TestRun.Status.FAILED
            if not task.error_summary:
                task.error_summary = "Jenkins summary artifact is missing."
        elif task.task_type != TestRun.RunType.DAILY_FULL and summary.get("allure_report_status") != "generated":
            task.status = TestRun.Status.FAILED
            allure_message = summary.get("allure_report_message") or summary.get("allure_report_status") or "unknown"
            task.error_summary = f"Allure HTML report was not generated: {allure_message}"
        elif summary.get("status") == "passed":
            task.status = TestRun.Status.SUCCESS
        elif summary.get("status") == "failed":
            task.status = TestRun.Status.TEST_FAILED
        else:
            task.status = TestRun.Status.FAILED

        if task.task_type == TestRun.RunType.FAILED_RERUN and task.status in {TestRun.Status.SUCCESS, TestRun.Status.TEST_FAILED}:
            apply_failed_rerun_summary(task, failed_nodeids)
        elif task.task_type == TestRun.RunType.DAILY_FULL and task.status in {
            TestRun.Status.SUCCESS,
            TestRun.Status.TEST_FAILED,
        }:
            case_sync_warning = apply_daily_parent_summary(task, summary)
            if case_sync_warning:
                task.status = TestRun.Status.FAILED
                task.error_summary = case_sync_warning
        elif task.status in {TestRun.Status.SUCCESS, TestRun.Status.TEST_FAILED}:
            case_sync_warning = apply_module_summary(task, summary)
            if case_sync_warning:
                task.error_summary = case_sync_warning

        if task.run:
            task.run.status = task.status
            task.run.summary_json = task.summary_json
            task.run.started_at = task.started_at
            task.run.finished_at = task.finished_at
            task.run.save(update_fields=["status", "summary_json", "started_at", "finished_at", "updated_at"])

        task.save(
            update_fields=[
                "jenkins_result",
                "summary_json",
                "failed_nodeids_json",
                "artifact_base_url",
                "summary_artifact_url",
                "failed_nodeids_artifact_url",
                "allure_report_url",
                "error_summary",
                "finished_at",
                "last_synced_at",
                "status",
                *identity_update_fields,
                "updated_at",
            ]
        )
        if task.status in TERMINAL_TASK_STATUSES:
            release_task_lock(task, f"task {task.status}")
        return task


def discover_jenkins_builds(*, job_full_names: list[str] | None = None, date: str | None = None) -> list[dict]:
    """发现 Jenkins 定时构建，按当前 active daily Job binding 限定扫描范围。"""
    resolved_job_names = job_full_names
    if resolved_job_names is None:
        resolved_job_names = list(
            JenkinsJobBinding.objects.filter(
                task_type=TestRun.RunType.DAILY_FULL,
                environment__isnull=True,
                module__isnull=True,
                is_active=True,
            )
            .order_by("job_full_name")
            .values_list("job_full_name", flat=True)
            .distinct()
        )
    if not resolved_job_names:
        return []
    return discover_jenkins_builds_from_jenkins(job_full_names=resolved_job_names, date=date)


def resolve_daily_parent_environment(binding: JenkinsJobBinding, build_result: dict) -> TestEnvironment:
    """Daily 只接受 global binding，并由构建产物精确解析环境。"""
    if binding.environment_id is not None or binding.module_id is not None:
        raise DailyParentEnvironmentError("Daily parent binding must be global.")
    raw_target_url = build_result.get("target_base_url")
    if not isinstance(raw_target_url, str) or not raw_target_url.strip():
        raise DailyParentEnvironmentError("Daily parent result does not contain a resolved target_base_url.")
    try:
        target_url = normalize_environment_base_url(raw_target_url)
    except ValueError as exc:
        raise DailyParentEnvironmentError("Daily parent target_base_url is invalid.") from exc
    environment = TestEnvironment.objects.filter(is_active=True, base_url=target_url).first()
    if environment is None:
        raise DailyParentEnvironmentError("Daily parent target_base_url is not an active environment.")
    return environment


def validate_existing_daily_parent_task(task: JenkinsTask, environment: TestEnvironment) -> None:
    """防止历史脏数据绕过 Daily 父任务的类型、模块和环境不变量。"""
    if (
        task.task_type != TestRun.RunType.DAILY_FULL
        or task.module_id is not None
        or task.environment_id != environment.id
        or task.run_id is None
    ):
        raise DailyParentEnvironmentError("Existing Daily parent task does not match the resolved environment.")
    run = task.run
    if (
        run is None
        or run.run_type != TestRun.RunType.DAILY_FULL
        or run.module_id is not None
        or run.environment_id != environment.id
    ):
        raise DailyParentEnvironmentError("Existing Daily parent task does not match the resolved environment.")


def create_or_get_daily_task_from_discovery(binding: JenkinsJobBinding, build_result: dict) -> tuple[JenkinsTask, bool]:
    # 先验证 global binding 与构建环境，避免既有任务路径绕过 Daily 约束。
    environment = resolve_daily_parent_environment(binding, build_result)
    build_number = build_result.get("build_number")
    task = JenkinsTask.objects.select_related("run").filter(
        job_full_name=binding.job_full_name,
        build_number=build_number,
    ).first()
    if task is not None:
        validate_existing_daily_parent_task(task, environment)
        return task, False

    run_key = build_result.get("run_id") or f"daily_full-{environment.id}-{build_number}"
    try:
        with transaction.atomic():
            run = TestRun.objects.create(
                run_key=run_key,
                run_type=TestRun.RunType.DAILY_FULL,
                environment=environment,
                module=None,
                status=TestRun.Status.RUNNING,
            )
            task = JenkinsTask.objects.create(
                run=run,
                environment=environment,
                module=None,
                task_type=TestRun.RunType.DAILY_FULL,
                trigger_source=JenkinsTask.TriggerSource.JENKINS_CRON,
                job_full_name=binding.job_full_name,
                build_number=build_number,
                jenkins_build_url=build_result.get("jenkins_build_url", ""),
                status=TestRun.Status.RUNNING,
            )
            return task, True
    except IntegrityError:
        # 另一 worker 可能已提交同一 run/build；事务回滚可避免留下孤立 TestRun。
        task = (
            JenkinsTask.objects.filter(job_full_name=binding.job_full_name, build_number=build_number)
            .select_related("run")
            .first()
        )
        if task is None:
            raise
        validate_existing_daily_parent_task(task, environment)
        return task, False


def catalog_error_response(exc: catalog_service.EnvironmentCatalogError) -> Response:
    """将目录服务的稳定错误码映射为冻结浏览器 API 契约。"""
    if isinstance(exc, catalog_service.EnvironmentCatalogBusyError):
        return api_error_response("environment_config_sync_busy", "已有活动的环境配置同步请求。", status.HTTP_409_CONFLICT)
    if isinstance(exc, catalog_service.EnvironmentCatalogDuplicateError):
        return api_error_response("duplicate_environment", "环境 key 或 base_url 已存在。", status.HTTP_409_CONFLICT)
    if isinstance(exc, catalog_service.EnvironmentCatalogSyncNotRetryableError):
        return api_error_response("sync_not_retryable", "当前同步请求不可直接重试。", status.HTTP_409_CONFLICT)
    if isinstance(exc, catalog_service.EnvironmentCatalogStateError):
        return api_error_response("invalid_sync_state", "同步请求状态不允许此操作。", status.HTTP_409_CONFLICT)
    if isinstance(exc, catalog_service.EnvironmentCatalogValidationError):
        if exc.code == "last_active_environment":
            return api_error_response("last_active_environment", str(exc), status.HTTP_409_CONFLICT)
        return api_error_response("validation_error", str(exc), status.HTTP_400_BAD_REQUEST)
    return api_error_response("environment_catalog_error", "环境目录操作失败。", status.HTTP_400_BAD_REQUEST)


def dispatch_environment_catalog_sync_attempt(attempt: EnvironmentCatalogSyncAttempt) -> EnvironmentCatalogSyncAttempt:
    """仅经 Jenkins API 排队专用配置同步 Job；排队失败时终结审计以释放重试键。"""

    def fail_dispatch(error_code: str) -> EnvironmentCatalogSyncAttempt:
        try:
            return catalog_service.fail_sync_attempt(
                attempt,
                error_code=error_code,
                error_summary="环境目录同步任务未能排队，请重试。",
            )
        except catalog_service.EnvironmentCatalogStateError as exc:
            logger.warning("Environment catalog dispatch state rejected: error_type=%s", type(exc).__name__)
            return EnvironmentCatalogSyncAttempt.objects.get(pk=attempt.pk)

    job_full_name = os.environ.get(
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME",
        "AiApiTest-DWP-Environment-Catalog-Sync",
    ).strip()
    if not job_full_name:
        return fail_dispatch("jenkins_job_name_missing")
    try:
        queue = trigger_jenkins_build(
            job_full_name=job_full_name,
            parameters={
                "SYNC_DIRECTION": attempt.direction,
                "SYNC_REQUEST_ID": attempt.request_id,
                "EXPECTED_YAML_BLOB_SHA": attempt.expected_yaml_blob_sha,
            },
        )
    except JenkinsServiceError as exc:
        # 外部异常文本可能包含地址或凭据，只记录异常类型。
        logger.warning("Environment catalog sync dispatch failed: error_type=%s", type(exc).__name__)
        return fail_dispatch("jenkins_dispatch_failed")
    queue_id = str(queue.get("queue_id") or "").strip()
    if not queue_id:
        return fail_dispatch("jenkins_queue_id_missing")
    try:
        return catalog_service.mark_sync_attempt_queued(attempt, queue_id=queue_id)
    except catalog_service.EnvironmentCatalogStateError as exc:
        logger.warning("Environment catalog queue state rejected: error_type=%s", type(exc).__name__)
        return EnvironmentCatalogSyncAttempt.objects.get(pk=attempt.pk)


def environment_catalog_write_response(environment: TestEnvironment, attempt: EnvironmentCatalogSyncAttempt) -> Response:
    attempt = dispatch_environment_catalog_sync_attempt(attempt)
    return Response(
        {
            "data": {
                "environment": EnvironmentCatalogEnvironmentSerializer(environment).data,
                "sync_attempt": EnvironmentCatalogSyncAttemptSerializer(attempt).data,
            }
        },
        status=status.HTTP_202_ACCEPTED,
    )


class TestEnvironmentListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询测试环境列表",
        description="登录用户查询环境；member 只读取启用环境，响应带目录状态。",
        parameters=[
            OpenApiParameter("is_active", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="是否筛选启用环境"),
        ],
        responses={
            200: EnvironmentCatalogListResponseSerializer,
            400: OpenApiResponse(ApiErrorResponseSerializer, description="is_active 参数非法：validation_error"),
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
        },
    )
    def get(self, request):
        raw_is_active = request.query_params.get("is_active")
        if raw_is_active is not None and raw_is_active.lower() not in {"true", "false"}:
            return api_error_response("validation_error", "is_active 仅支持 true 或 false。", status.HTTP_400_BAD_REQUEST)
        queryset = TestEnvironment.objects.all()
        if is_admin(request.user):
            if raw_is_active is not None:
                queryset = queryset.filter(is_active=raw_is_active.lower() == "true")
        else:
            queryset = queryset.filter(is_active=True)
        catalog_state, _ = EnvironmentCatalogState.objects.get_or_create(
            catalog_key=EnvironmentCatalogState.CATALOG_KEY
        )
        return Response(
            {
                "data": EnvironmentCatalogEnvironmentSerializer(queryset, many=True).data,
                "catalog_state": EnvironmentCatalogStateSerializer(catalog_state).data,
            }
        )

    @extend_schema(
        tags=["通过率"],
        summary="新增测试环境并发起 YAML 写回",
        request=TestEnvironmentCreateRequestSerializer,
        responses={
            202: EnvironmentCatalogWriteEnvelopeSerializer,
            400: OpenApiResponse(ApiErrorResponseSerializer, description="请求参数非法：validation_error"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="环境重复或已有活动同步"),
        },
    )
    def post(self, request):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        serializer = TestEnvironmentCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response("validation_error", "请求参数校验失败。", status.HTTP_400_BAD_REQUEST)
        try:
            environment, attempt = catalog_service.create_environment_with_sync(
                requested_by=request.user,
                **serializer.validated_data,
            )
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        return environment_catalog_write_response(environment, attempt)


class TestEnvironmentDetailView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def _get_environment(self, environment_id: int) -> TestEnvironment | None:
        return TestEnvironment.objects.filter(id=environment_id).first()

    @extend_schema(
        tags=["通过率"],
        summary="编辑测试环境并发起 YAML 写回",
        request=TestEnvironmentUpdateRequestSerializer,
        responses={
            202: EnvironmentCatalogWriteEnvelopeSerializer,
            400: OpenApiResponse(ApiErrorResponseSerializer, description="请求参数非法：validation_error"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="环境不存在：environment_not_found"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="同步冲突或最后一个启用环境不可停用"),
        },
    )
    def patch(self, request, environment_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        environment = self._get_environment(environment_id)
        if environment is None:
            return api_error_response("environment_not_found", "测试环境不存在。", status.HTTP_404_NOT_FOUND)
        serializer = TestEnvironmentUpdateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error_response("validation_error", "请求参数校验失败。", status.HTTP_400_BAD_REQUEST)
        values = serializer.validated_data
        try:
            updated, attempt = catalog_service.update_environment_with_sync(
                environment,
                url_name=values.get("url_name", environment.env_name),
                base_url=values.get("base_url", environment.base_url),
                url_desc=values.get("url_desc", environment.url_desc),
                is_active=values.get("is_active", environment.is_active),
                requested_by=request.user,
            )
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        return environment_catalog_write_response(updated, attempt)

    @extend_schema(
        tags=["通过率"],
        summary="逻辑停用测试环境并发起 YAML 写回",
        responses={
            202: EnvironmentCatalogWriteEnvelopeSerializer,
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="环境不存在：environment_not_found"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="同步冲突或最后一个启用环境不可停用"),
        },
    )
    def delete(self, request, environment_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        environment = self._get_environment(environment_id)
        if environment is None:
            return api_error_response("environment_not_found", "测试环境不存在。", status.HTTP_404_NOT_FOUND)
        try:
            updated, attempt = catalog_service.set_environment_active_with_sync(
                environment,
                is_active=False,
                requested_by=request.user,
            )
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        return environment_catalog_write_response(updated, attempt)


class TestEnvironmentSyncFromYamlView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="发起隔离 checkout 的 YAML 环境导入",
        responses={
            202: EnvironmentCatalogSyncAttemptResponseSerializer,
            400: OpenApiResponse(ApiErrorResponseSerializer, description="请求体必须为空：validation_error"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="已有活动同步：environment_config_sync_busy"),
        },
    )
    def post(self, request):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        if request.data:
            return api_error_response("validation_error", "同步导入请求不接受请求体。", status.HTTP_400_BAD_REQUEST)
        try:
            attempt = catalog_service.create_yaml_to_mysql_sync_attempt(requested_by=request.user)
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        attempt = dispatch_environment_catalog_sync_attempt(attempt)
        return Response({"data": EnvironmentCatalogSyncAttemptSerializer(attempt).data}, status=status.HTTP_202_ACCEPTED)


class EnvironmentCatalogSyncAttemptDetailView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询环境目录同步审计",
        responses={
            200: EnvironmentCatalogSyncAttemptResponseSerializer,
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="同步请求不存在：environment_catalog_sync_not_found"),
        },
    )
    def get(self, request, attempt_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        attempt = EnvironmentCatalogSyncAttempt.objects.select_related("requested_by").filter(id=attempt_id).first()
        if attempt is None:
            return api_error_response("environment_catalog_sync_not_found", "环境目录同步请求不存在。", status.HTTP_404_NOT_FOUND)
        return Response({"data": EnvironmentCatalogSyncAttemptSerializer(attempt).data})


class EnvironmentCatalogSyncAttemptRetryView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="重试失败的环境目录同步请求",
        responses={
            202: EnvironmentCatalogSyncAttemptResponseSerializer,
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="同步请求不存在：environment_catalog_sync_not_found"),
            409: OpenApiResponse(ApiErrorResponseSerializer, description="同步请求不可重试或已有活动同步"),
        },
    )
    def post(self, request, attempt_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        attempt = EnvironmentCatalogSyncAttempt.objects.filter(id=attempt_id).first()
        if attempt is None:
            return api_error_response("environment_catalog_sync_not_found", "环境目录同步请求不存在。", status.HTTP_404_NOT_FOUND)
        try:
            retry_attempt = catalog_service.retry_sync_attempt(attempt, requested_by=request.user)
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        retry_attempt = dispatch_environment_catalog_sync_attempt(retry_attempt)
        return Response({"data": EnvironmentCatalogSyncAttemptSerializer(retry_attempt).data}, status=status.HTTP_202_ACCEPTED)


SAFE_CATALOG_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class InternalEnvironmentCatalogView(APIView):
    authentication_classes = []
    permission_classes = []

    def authorize(self, request) -> Response | None:
        configured_token = settings.ENVIRONMENT_CATALOG_SERVICE_TOKEN
        authorization = request.headers.get("Authorization", "")
        expected = f"Bearer {configured_token}" if configured_token else ""
        if not expected or not secrets.compare_digest(authorization, expected):
            return api_error_response("internal_service_unauthorized", "内部服务令牌无效。", status.HTTP_403_FORBIDDEN)
        return None

    def get_attempt(self, sync_request_id: str) -> EnvironmentCatalogSyncAttempt | Response:
        if not SAFE_CATALOG_REQUEST_ID.fullmatch(sync_request_id):
            return api_error_response("validation_error", "同步请求标识非法。", status.HTTP_400_BAD_REQUEST)
        attempt = EnvironmentCatalogSyncAttempt.objects.filter(request_id=sync_request_id).first()
        if attempt is None:
            return api_error_response("environment_catalog_sync_not_found", "环境目录同步请求不存在。", status.HTTP_404_NOT_FOUND)
        return attempt


class EnvironmentCatalogSyncExportView(InternalEnvironmentCatalogView):
    """固定 Jenkins Job 下载冻结的 MySQL 写回目录，不使用浏览器 JWT。"""

    @extend_schema(exclude=True)
    def get(self, request, sync_request_id: str):
        unauthorized = self.authorize(request)
        if unauthorized is not None:
            return unauthorized
        attempt = self.get_attempt(sync_request_id)
        if isinstance(attempt, Response):
            return attempt
        if attempt.direction != EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML:
            return api_error_response("invalid_sync_direction", "当前同步请求不支持导出。", status.HTTP_409_CONFLICT)
        try:
            if attempt.status == EnvironmentCatalogSyncAttempt.Status.QUEUED:
                attempt = catalog_service.mark_sync_attempt_running(attempt)
            elif attempt.status != EnvironmentCatalogSyncAttempt.Status.RUNNING:
                raise catalog_service.EnvironmentCatalogStateError("同步请求不能导出。")
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        # CLI 约定顶层直接为 YAML mapping，不能包裹浏览器 data 信封。
        return Response(attempt.payload_json)


class EnvironmentCatalogSyncCallbackView(InternalEnvironmentCatalogView):
    """只处理固定 Jenkins Job 的结构化结果，不返回令牌、内部 URL 或工作区路径。"""

    def invalid_callback_schema_response(self, attempt: EnvironmentCatalogSyncAttempt) -> Response:
        """把活动请求释放为 failed，避免错误回调永久占用同步键。"""
        if attempt.status in attempt.ACTIVE_STATUSES:
            try:
                catalog_service.fail_sync_attempt(
                    attempt,
                    error_code="callback_schema_invalid",
                    error_summary="同步回调字段校验失败，请修正后重试。",
                )
            except catalog_service.EnvironmentCatalogError:
                # 终态并发完成时维持既有状态，浏览器仍只收到脱敏的 400 语义。
                pass
        return api_error_response("validation_error", "同步回调字段非法。", status.HTTP_400_BAD_REQUEST)

    @extend_schema(exclude=True)
    def post(self, request, sync_request_id: str):
        unauthorized = self.authorize(request)
        if unauthorized is not None:
            return unauthorized
        attempt = self.get_attempt(sync_request_id)
        if isinstance(attempt, Response):
            return attempt
        payload = request.data
        if not isinstance(payload, dict) or payload.get("direction") != attempt.direction:
            return self.invalid_callback_schema_response(attempt)
        if payload.get("expected_yaml_blob_sha") != attempt.expected_yaml_blob_sha:
            return self.invalid_callback_schema_response(attempt)
        if attempt.direction == EnvironmentCatalogSyncAttempt.Direction.YAML_TO_MYSQL:
            allowed = {"direction", "expected_yaml_blob_sha", "observed_yaml_blob_sha", "catalog", "commit_sha"}
            required = {"observed_yaml_blob_sha", "catalog"}
        else:
            allowed = {
                "direction",
                "expected_yaml_blob_sha",
                "observed_yaml_blob_sha",
                "written_yaml_blob_sha",
                "commit_sha",
            }
            required = {"observed_yaml_blob_sha", "written_yaml_blob_sha"}
        if set(payload) - allowed or required - set(payload):
            return self.invalid_callback_schema_response(attempt)
        try:
            if attempt.status == EnvironmentCatalogSyncAttempt.Status.QUEUED:
                attempt = catalog_service.mark_sync_attempt_running(attempt)
            if attempt.direction == EnvironmentCatalogSyncAttempt.Direction.YAML_TO_MYSQL:
                completed, _ = catalog_service.complete_yaml_to_mysql_sync_attempt(
                    attempt,
                    catalog=payload["catalog"],
                    observed_yaml_blob_sha=payload["observed_yaml_blob_sha"],
                    commit_sha=payload.get("commit_sha", ""),
                )
            else:
                completed = catalog_service.complete_mysql_to_yaml_sync_attempt(
                    attempt,
                    observed_yaml_blob_sha=payload["observed_yaml_blob_sha"],
                    written_yaml_blob_sha=payload["written_yaml_blob_sha"],
                    commit_sha=payload.get("commit_sha"),
                )
        except catalog_service.EnvironmentCatalogError as exc:
            return catalog_error_response(exc)
        return Response({"data": EnvironmentCatalogSyncAttemptSerializer(completed).data})


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
            OpenApiParameter("module_name", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模块名称，逗号分隔多选，精确匹配"),
            OpenApiParameter("package_name", OpenApiTypes.STR, OpenApiParameter.QUERY, description="用例包名，逗号分隔多选，精确匹配"),
            OpenApiParameter("module_dev", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模块开发，逗号分隔多选，精确匹配"),
            OpenApiParameter("module_test", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模块测试，逗号分隔多选，精确匹配"),
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
            ("module_test", "module__module_test__in"),
            ("module_name", "module__module_name__in"),
            ("module_dev", "module__module_dev__in"),
            ("package_name", "module__package_name__in"),
        ]:
            values = parse_multi_select_values(param_name, request.query_params.get(param_name))
            if isinstance(values, Response):
                return values
            if values:
                queryset = queryset.filter(**{lookup: values})
        if pass_rate_lte is not None:
            queryset = queryset.filter(pass_rate__lte=pass_rate_lte)
        queryset = queryset.order_by(*sort_fields)
        return paginated_response_with_context(queryset, ModuleSnapshotSerializer, page, per_page, {"request": request})


class ModuleSnapshotFilterOptionsView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询模块通过率筛选下拉选项",
        description="登录用户按环境查询模块名称、用例包名、模块开发和模块测试的去重多选项。",
        parameters=[
            OpenApiParameter("environment_id", OpenApiTypes.INT, OpenApiParameter.QUERY, required=True, description="测试环境 ID"),
        ],
        responses={
            200: ModuleSnapshotFilterOptionsResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效：authentication_required"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="环境参数非法：validation_error"),
        },
    )
    def get(self, request):
        environment_id = parse_environment_id(request.query_params.get("environment_id"))
        if isinstance(environment_id, Response):
            return environment_id
        if not TestEnvironment.objects.filter(id=environment_id, is_active=True).exists():
            return validation_error("environment_id 无效。")

        try:
            options = build_filter_options_from_package_module_yaml()
        except ImproperlyConfigured as exc:
            return api_error_response(
                "module_metadata_unavailable",
                str(exc),
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"data": options})


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


class FailedCaseRetryCreateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @transaction.atomic
    def post(self, request, snapshot_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)

        snapshot = get_active_snapshot(snapshot_id)
        if snapshot is None:
            return api_error_response("module_snapshot_not_found", "模块快照不存在。", status.HTTP_404_NOT_FOUND)

        binding = get_job_binding(snapshot, TestRun.RunType.FAILED_RERUN)
        if binding is None:
            return api_error_response("jenkins_job_not_configured", "Jenkins Job 未配置。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        retry_scope = request.data.get("retry_scope")
        if retry_scope not in {"all_failed", "selected_failed"}:
            return validation_error("retry_scope 必须为 all_failed 或 selected_failed。")

        cases = TestCaseResult.objects.filter(
            environment=snapshot.environment,
            module=snapshot.module,
            module_snapshot=snapshot,
            is_current=True,
            display_status=TestCaseResult.DisplayStatus.FAILED,
        )
        if retry_scope == "selected_failed":
            raw_ids = request.data.get("case_result_ids") or []
            if not isinstance(raw_ids, list) or not raw_ids:
                return api_error_response("invalid_case_selection", "勾选用例不可重试。", status.HTTP_422_UNPROCESSABLE_ENTITY)
            cases = cases.filter(id__in=raw_ids)
            if cases.count() != len(set(raw_ids)):
                return api_error_response("invalid_case_selection", "勾选用例不可重试。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        nodeids = sorted({case.node_id for case in cases})
        if not nodeids:
            return api_error_response("no_failed_cases", "通过率 100% 无需失败重试。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        parameters = {
            "CASE_PATH": snapshot.module.case_path,
            "PYTEST_NODE_IDS": "\n".join(nodeids),
            "RETRY_MODE": "selected",
            "RETRY_COUNT": str(binding.default_retry_count),
            "CLEAN_ALLURE": "true",
            "OPEN_REPORT": "false",
        }
        task = create_queued_jenkins_task(
            snapshot=snapshot,
            task_type=TestRun.RunType.FAILED_RERUN,
            triggered_by=request.user,
            binding=binding,
            parameters=parameters,
            requested_nodeids=nodeids,
        )
        if isinstance(task, Response):
            return task
        return jenkins_task_response(task, request, status.HTTP_202_ACCEPTED)


class ModuleRerunCreateView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def post(self, request, snapshot_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)

        snapshot = get_active_snapshot(snapshot_id)
        if snapshot is None:
            return api_error_response("module_snapshot_not_found", "模块快照不存在。", status.HTTP_404_NOT_FOUND)
        if not snapshot.module.case_path:
            return api_error_response("module_case_path_missing", "模块用例路径缺失。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        binding = get_job_binding(snapshot, TestRun.RunType.MODULE_RERUN)
        if binding is None:
            return api_error_response("jenkins_job_not_configured", "Jenkins Job 未配置。", status.HTTP_422_UNPROCESSABLE_ENTITY)

        parameters = {
            "CASE_PATH": snapshot.module.case_path,
            "MODULE_NAME": snapshot.module.module_name,
            "RETRY_MODE": "module",
            "RETRY_COUNT": str(binding.default_retry_count),
            "CLEAN_ALLURE": "true",
            "OPEN_REPORT": "false",
        }
        task = create_queued_jenkins_task(
            snapshot=snapshot,
            task_type=TestRun.RunType.MODULE_RERUN,
            triggered_by=request.user,
            binding=binding,
            parameters=parameters,
        )
        if isinstance(task, Response):
            return task
        return jenkins_task_response(task, request, status.HTTP_202_ACCEPTED)


class ModuleSnapshotJenkinsTasksView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["Jenkins"],
        summary="查询当前模块 Jenkins 任务",
        description="登录用户查询当前模块的 Jenkins 任务弹窗数据，支持日期、状态、任务类型和分页筛选。",
        parameters=[
            OpenApiParameter("snapshot_id", OpenApiTypes.INT, OpenApiParameter.PATH, description="模块快照 ID"),
            OpenApiParameter("date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="任务日期，today 或 YYYY-MM-DD，默认 today"),
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, description="任务状态枚举"),
            OpenApiParameter("task_type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="任务类型：daily_full/failed_rerun/module_rerun"),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，从 1 开始"),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页条数，范围 1-100"),
        ],
        responses={
            200: JenkinsTaskListResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="模块快照不存在：module_snapshot_not_found"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="日期、状态、任务类型或分页参数非法：validation_error"),
        },
    )
    def get(self, request, snapshot_id: int):
        snapshot = get_active_snapshot(snapshot_id)
        if snapshot is None:
            return api_error_response("module_snapshot_not_found", "模块快照不存在。", status.HTTP_404_NOT_FOUND)
        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination

        queryset = JenkinsTask.objects.select_related("environment", "module", "triggered_by").filter(
            environment=snapshot.environment,
            module=snapshot.module,
        )
        date_value = request.query_params.get("date", "today")
        if date_value == "today":
            queryset = queryset.filter(created_at__date=timezone.localdate())
        elif date_value:
            try:
                parsed_date = timezone.datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                return validation_error("date 必须为 today 或 YYYY-MM-DD。")
            queryset = queryset.filter(created_at__date=parsed_date)
        status_value = request.query_params.get("status")
        if status_value:
            allowed_statuses = {choice[0] for choice in TestRun.Status.choices}
            if status_value not in allowed_statuses:
                return validation_error("任务状态筛选非法。")
            queryset = queryset.filter(status=status_value)
        task_type = request.query_params.get("task_type")
        if task_type:
            allowed_task_types = {choice[0] for choice in TestRun.RunType.choices}
            if task_type not in allowed_task_types:
                return validation_error("任务类型筛选非法。")
            queryset = queryset.filter(task_type=task_type)

        total = queryset.count()
        start = (page - 1) * per_page
        end = start + per_page
        total_pages = (total + per_page - 1) // per_page if total else 0
        serializer = JenkinsTaskSerializer(queryset[start:end], many=True, context={"request": request})
        return Response(
            {
                "data": serializer.data,
                "meta": {"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
            }
        )


class JenkinsTaskCancelView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def post(self, request, task_id: int):
        task = JenkinsTask.objects.select_related("triggered_by", "environment", "module").filter(id=task_id).first()
        if task is None:
            return api_error_response("jenkins_task_not_found", "Jenkins 任务不存在。", status.HTTP_404_NOT_FOUND)
        if not (is_admin(request.user) or task.triggered_by_id == getattr(request.user, "id", None)):
            return api_error_response("forbidden", "无取消权限。", status.HTTP_403_FORBIDDEN)
        if task.status == TestRun.Status.CANCELING:
            return jenkins_task_response(task, request, status.HTTP_202_ACCEPTED)
        if task.status not in {TestRun.Status.QUEUED, TestRun.Status.RUNNING}:
            return api_error_response("task_not_cancelable", "任务不可取消。", status.HTTP_409_CONFLICT)
        try:
            cancel_jenkins_task(task)
        except JenkinsServiceError as exc:
            if is_jenkins_task_not_found_error(exc):
                return api_error_response(
                    "task_not_cancelable",
                    "任务已不在 Jenkins 队列中，请同步状态后重试。",
                    status.HTTP_409_CONFLICT,
                )
            return api_error_response("jenkins_unavailable", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)
        task.status = TestRun.Status.CANCELING
        if task.run:
            task.run.status = TestRun.Status.CANCELING
            task.run.save(update_fields=["status", "updated_at"])
        task.save(update_fields=["status", "updated_at"])
        return jenkins_task_response(task, request, status.HTTP_202_ACCEPTED)


class JenkinsTaskSyncView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        operation_id="jenkins_task_sync",
        summary="同步单个 Jenkins 任务",
        description="queue 404 时会按 queueId 或 RUN_ID 精确恢复 build；未找到且未超时则保持 queued。",
        request=None,
        responses={
            200: JenkinsTaskResponseSerializer,
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            404: OpenApiResponse(ApiErrorResponseSerializer, description="Jenkins 任务不存在：jenkins_task_not_found"),
            409: OpenApiResponse(
                ApiErrorResponseSerializer,
                description="多个 Jenkins build 精确匹配，任务状态保持不变：jenkins_build_ambiguous",
            ),
            503: OpenApiResponse(
                ApiErrorResponseSerializer,
                description="Jenkins 服务真实不可用：jenkins_unavailable；单个 queue 404 不属于此错误",
            ),
        },
    )
    def post(self, request, task_id: int):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)
        task = JenkinsTask.objects.filter(id=task_id).first()
        if task is None:
            return api_error_response("jenkins_task_not_found", "Jenkins 任务不存在。", status.HTTP_404_NOT_FOUND)
        try:
            result = fetch_jenkins_task_result(task)
        except JenkinsBuildMatchError as exc:
            record_jenkins_build_match_error(task, exc)
            return api_error_response("jenkins_build_ambiguous", str(exc), status.HTTP_409_CONFLICT)
        except JenkinsServiceError as exc:
            return api_error_response("jenkins_unavailable", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)
        synced = sync_task_with_result(task, result)
        return jenkins_task_response(synced, request)


class JenkinsTaskBulkSyncView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        operation_id="jenkins_task_bulk_sync",
        summary="发现并同步 Jenkins 每日全量任务",
        description="按 active Daily Job 逐个发现构建，重复调用保持幂等。",
        request=JenkinsTaskBulkSyncRequestSerializer,
        responses={
            200: OpenApiResponse(
                JenkinsTaskBulkSyncResponseSerializer,
                description="同步完成；单个 Job、build 失败或构建匹配歧义会被隔离并继续处理其它任务",
            ),
            401: OpenApiResponse(ApiErrorResponseSerializer, description="未登录或 Cookie 无效"),
            403: OpenApiResponse(ApiErrorResponseSerializer, description="需要管理人员权限：admin_required"),
            422: OpenApiResponse(ApiErrorResponseSerializer, description="请求参数非法：validation_error"),
            503: OpenApiResponse(
                ApiErrorResponseSerializer,
                description="全部配置 Job 均不可访问或所有已发现 build 均同步失败：jenkins_unavailable",
            ),
        },
    )
    def post(self, request):
        if not is_admin(request.user):
            return api_error_response("admin_required", "需要管理人员权限。", status.HTTP_403_FORBIDDEN)

        request_serializer = JenkinsTaskBulkSyncRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return validation_error("discover_daily 或 date 参数非法。")
        if request_serializer.validated_data["discover_daily"] is not True:
            return validation_error("discover_daily 必须为 true。")
        requested_date = request_serializer.validated_data.get("date")
        date = requested_date.isoformat() if requested_date else None

        created_count = 0
        updated_count = 0
        synced_count = 0
        daily_job_names = list(
            JenkinsJobBinding.objects.filter(
                task_type=TestRun.RunType.DAILY_FULL,
                environment__isnull=True,
                module__isnull=True,
                is_active=True,
            )
            .order_by("job_full_name")
            .values_list("job_full_name", flat=True)
            .distinct()
        )
        discovered = []
        discovery_success_count = 0
        first_discovery_error: JenkinsServiceError | None = None
        for job_index, job_full_name in enumerate(daily_job_names, start=1):
            try:
                discovered.extend(
                    discover_jenkins_builds(job_full_names=[job_full_name], date=date)
                )
                discovery_success_count += 1
            except JenkinsBuildMatchError as exc:
                logger.warning(
                    "Jenkins Daily Job discovery ambiguous: job_index=%s error_type=%s",
                    job_index,
                    type(exc).__name__,
                )
            except JenkinsServiceError as exc:
                first_discovery_error = first_discovery_error or exc
                # 外部错误信息可能包含内部 URL，仅记录序号和异常类型。
                logger.warning(
                    "Jenkins Daily Job discovery failed: job_index=%s error_type=%s",
                    job_index,
                    type(exc).__name__,
                )
        if daily_job_names and discovery_success_count == 0:
            return api_error_response(
                "jenkins_unavailable",
                str(first_discovery_error),
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        first_sync_error: JenkinsServiceError | None = None
        for build_result in discovered:
            job_full_name = build_result.get("job_full_name")
            build_number = build_result.get("build_number")
            if not job_full_name or build_number is None:
                continue
            binding = JenkinsJobBinding.objects.select_related("environment", "module").filter(
                task_type=TestRun.RunType.DAILY_FULL,
                environment__isnull=True,
                module__isnull=True,
                job_full_name=job_full_name,
                is_active=True,
            ).first()
            if binding is None:
                continue
            try:
                task, created = create_or_get_daily_task_from_discovery(binding, build_result)
            except DailyParentEnvironmentError as exc:
                logger.warning(
                    "Jenkins Daily parent was skipped: job_index=%s error_type=%s",
                    job_full_name,
                    type(exc).__name__,
                )
                continue
            if created:
                created_count += 1
            else:
                updated_count += 1
            if "summary" in build_result or build_result.get("building") or build_result.get("canceled"):
                sync_result = build_result
            else:
                try:
                    sync_result = fetch_jenkins_task_result(task)
                except JenkinsBuildMatchError as exc:
                    record_jenkins_build_match_error(task, exc)
                    logger.warning(
                        "Jenkins Daily build sync ambiguous: task_id=%s error_type=%s",
                        task.id,
                        type(exc).__name__,
                    )
                    continue
                except JenkinsServiceError as exc:
                    first_sync_error = first_sync_error or exc
                    logger.warning(
                        "Jenkins Daily build sync failed: task_id=%s error_type=%s",
                        task.id,
                        type(exc).__name__,
                    )
                    continue
            sync_task_with_result(task, sync_result)
            synced_count += 1

        if discovered and synced_count == 0 and first_sync_error is not None:
            return api_error_response(
                "jenkins_unavailable",
                str(first_sync_error),
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "data": {
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "synced_count": synced_count,
                }
            }
        )


class JenkinsTaskListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    def get(self, request):
        pagination = parse_pagination(request)
        if isinstance(pagination, Response):
            return pagination
        page, per_page = pagination
        queryset = JenkinsTask.objects.select_related("environment", "module", "triggered_by").all()
        for param_name in ["environment_id", "module_id", "task_type", "status"]:
            value = request.query_params.get(param_name)
            if value:
                queryset = queryset.filter(**{param_name: value})
        total = queryset.count()
        start = (page - 1) * per_page
        end = start + per_page
        total_pages = (total + per_page - 1) // per_page if total else 0
        serializer = JenkinsTaskSerializer(queryset[start:end], many=True, context={"request": request})
        return Response({"data": serializer.data, "meta": {"total": total, "page": page, "per_page": per_page, "total_pages": total_pages}})


def select_daily_trend_rows(rows) -> list[ModuleRunHistory]:
    """每天优选一条趋势：模块重试优先，同类型取最后完成记录。"""
    selected: dict = {}
    for row in rows:
        current = selected.get(row.run_date)
        if current is None:
            selected[row.run_date] = row
            continue

        row_is_module_rerun = row.run_type == TestRun.RunType.MODULE_RERUN
        current_is_module_rerun = current.run_type == TestRun.RunType.MODULE_RERUN
        if row_is_module_rerun != current_is_module_rerun:
            if row_is_module_rerun:
                selected[row.run_date] = row
            continue

        if current.completed_at is None:
            is_later = row.completed_at is not None or row.id > current.id
        elif row.completed_at is None:
            is_later = False
        elif row.completed_at == current.completed_at:
            is_later = row.id > current.id
        else:
            is_later = row.completed_at > current.completed_at
        if is_later:
            selected[row.run_date] = row

    return [selected[run_date] for run_date in sorted(selected)]


class ModuleSnapshotTrendView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = []

    @extend_schema(
        tags=["通过率"],
        summary="查询模块通过率趋势",
        description=(
            "登录用户查询指定模块近 7 天或 30 天通过率趋势。每个日期最多返回一条；"
            "同日模块重试优先并选择最后完成记录。窗口结束于请求当天，仅返回真实历史，缺失日期不补零。"
            "days 不是 7 或 30 时返回校验错误。"
        ),
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

        window_end = timezone.localdate()
        window_start = window_end - timezone.timedelta(days=days - 1)
        history_rows = (
            ModuleRunHistory.objects.filter(
                environment=snapshot.environment,
                module=snapshot.module,
                run_date__gte=window_start,
                run_date__lte=window_end,
            )
            .order_by("run_date", "completed_at", "id")
        )
        series = select_daily_trend_rows(history_rows)
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
