from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from django.views.static import serve
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import PlatformAccessPermission

from .models import FailureCase, TestRun
from .serializers import (
    FailureCaseSerializer,
    RetryCountSerializer,
    RetryModuleSerializer,
    RetrySelectedSerializer,
    TestRunCreateSerializer,
    TestRunSerializer,
)
from .services.allure_results_parser import parse_allure_failures
from .services.api_test_runner import ApiTestRunner


class TestRunViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]
    serializer_class = TestRunSerializer

    def get_queryset(self):
        return TestRun.objects.select_related("triggered_by", "parent_run").annotate(
            failure_count=Count("failures")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(
            {
                "count": queryset.count(),
                "results": self.get_serializer(queryset, many=True).data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = TestRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = ApiTestRunner.run(
            case_path=serializer.validated_data["case_path"],
            node_ids=serializer.validated_data.get("node_ids", []),
            retry_mode=serializer.validated_data["retry_mode"],
            retry_count=serializer.validated_data["retry_count"],
        )
        test_run = register_test_run_from_summary(
            summary=summary,
            user=request.user,
            trigger_source=TestRun.TriggerSource.API,
        )
        output = self.get_serializer(self.get_queryset().get(pk=test_run.pk))
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="failures")
    def failures(self, request, pk=None):
        test_run = self.get_object()
        failures = test_run.failures.all()
        return Response(
            {
                "count": failures.count(),
                "results": FailureCaseSerializer(failures, many=True).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="retry-selected")
    def retry_selected(self, request, pk=None):
        original = self.get_object()
        serializer = RetrySelectedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failures = list(
            original.failures.filter(id__in=serializer.validated_data["failure_ids"])
        )
        node_ids = [failure.node_id for failure in failures]
        summary = ApiTestRunner.run(
            case_path=original.case_path,
            node_ids=node_ids,
            retry_mode=TestRun.RetryMode.SELECTED,
            retry_count=serializer.validated_data["retry_count"],
        )
        retry_run = register_test_run_from_summary(
            summary=summary,
            user=request.user,
            trigger_source=TestRun.TriggerSource.API,
            parent_run=original,
        )
        _mark_retry_result(failures, retry_run)
        output = self.get_serializer(self.get_queryset().get(pk=retry_run.pk))
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="retry-all-failed")
    def retry_all_failed(self, request, pk=None):
        original = self.get_object()
        serializer = RetryCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failures = list(original.failures.filter(status=FailureCase.Status.FAILED))
        node_ids = [failure.node_id for failure in failures]
        summary = ApiTestRunner.run(
            case_path=original.case_path,
            node_ids=node_ids,
            retry_mode=TestRun.RetryMode.ALL_FAILED,
            retry_count=serializer.validated_data["retry_count"],
        )
        retry_run = register_test_run_from_summary(
            summary=summary,
            user=request.user,
            trigger_source=TestRun.TriggerSource.API,
            parent_run=original,
        )
        _mark_retry_result(failures, retry_run)
        output = self.get_serializer(self.get_queryset().get(pk=retry_run.pk))
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="retry-module")
    def retry_module(self, request, pk=None):
        original = self.get_object()
        serializer = RetryModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = ApiTestRunner.run(
            case_path=serializer.validated_data["module_path"],
            node_ids=[],
            retry_mode=TestRun.RetryMode.MODULE,
            retry_count=serializer.validated_data["retry_count"],
        )
        retry_run = register_test_run_from_summary(
            summary=summary,
            user=request.user,
            trigger_source=TestRun.TriggerSource.API,
            parent_run=original,
        )
        output = self.get_serializer(self.get_queryset().get(pk=retry_run.pk))
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        test_run = self.get_object()
        if not _report_index_exists(test_run):
            return Response(
                {"detail": "Report is not available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "report_url": f"/reports/{test_run.run_id}/",
                "run_id": test_run.run_id,
            }
        )


def serve_allure_report(request, run_id: str, path: str = "index.html"):
    test_run = TestRun.objects.filter(run_id=run_id).first()
    if not test_run or not _report_index_exists(test_run):
        raise Http404("Report is not available.")
    safe_path = path or "index.html"
    return serve(request, safe_path, document_root=_resolve_report_dir(test_run))


def register_test_run_from_summary(
    *,
    summary: dict,
    user,
    trigger_source: str,
    parent_run: TestRun | None = None,
) -> TestRun:
    now = timezone.now()
    test_run = TestRun.objects.create(
        run_id=summary["run_id"],
        case_path=summary.get("case_path") or "",
        node_ids=summary.get("node_ids") or [],
        retry_mode=summary.get("retry_mode") or TestRun.RetryMode.NONE,
        retry_count=summary.get("retry_count") or 0,
        status=_status_from_summary(summary),
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
        trigger_source=trigger_source,
        parent_run=parent_run,
        report_path=summary.get("allure_report_dir") or "",
        allure_results_path=summary.get("allure_results_dir") or "",
        console_log_path=summary.get("console_log_path") or "",
        started_at=now,
        finished_at=now,
        summary=summary,
    )
    _record_failure_cases(test_run, summary)
    return test_run


def _report_index_exists(test_run: TestRun) -> bool:
    report_dir = _resolve_report_dir(test_run)
    if report_dir is None:
        return False
    return (report_dir / "index.html").is_file()


def _resolve_report_dir(test_run: TestRun) -> Path | None:
    if not test_run.report_path:
        return None
    report_dir = Path(test_run.report_path).resolve()
    report_root = Path(settings.ALLURE_REPORTS_ROOT).resolve()
    try:
        report_dir.relative_to(report_root)
    except ValueError:
        return None
    return report_dir


def _record_failure_cases(test_run: TestRun, summary: dict) -> None:
    failures = []
    allure_results_dir = summary.get("allure_results_dir")
    if allure_results_dir:
        failures = parse_allure_failures(Path(allure_results_dir))
    if not failures:
        failures = [
            _failure_from_node_id(node_id)
            for node_id in summary.get("failed_nodeids", [])
        ]
    for failure in failures:
        FailureCase.objects.create(
            test_run=test_run,
            node_id=failure["node_id"],
            case_name=failure["case_name"],
            module_path=failure["module_path"],
            description=failure.get("description", ""),
            error_type=failure.get("error_type", ""),
            assertion_message=failure.get("assertion_message", ""),
            status=failure.get("status") or FailureCase.Status.FAILED,
        )


def _failure_from_node_id(node_id: str) -> dict:
    case_name = node_id.rsplit("::", 1)[-1] if "::" in node_id else node_id
    module_path = node_id.split(".py", 1)[0]
    if "/" in module_path:
        module_path = module_path.rsplit("/", 1)[0]
    return {
        "node_id": node_id,
        "case_name": case_name,
        "module_path": module_path,
        "description": "",
        "error_type": "",
        "assertion_message": "",
        "status": FailureCase.Status.FAILED,
    }


def _status_from_summary(summary: dict) -> str:
    status_value = summary.get("status")
    if status_value in TestRun.Status.values:
        return status_value
    return TestRun.Status.PASSED if summary.get("return_code") == 0 else TestRun.Status.FAILED


def _mark_retry_result(failures: list[FailureCase], retry_run: TestRun) -> None:
    retry_status = (
        FailureCase.RetryStatus.PASSED
        if retry_run.status == TestRun.Status.PASSED
        else FailureCase.RetryStatus.FAILED
    )
    for failure in failures:
        failure.retry_status = retry_status
        failure.last_retry_run = retry_run
        failure.save(update_fields=["retry_status", "last_retry_run", "updated_at"])
