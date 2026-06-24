"""测试任务 API 与报告服务模块。
本模块提供测试任务创建、列表、详情、失败用例查询、失败重试和 Allure 报告入口。
同时包含把 api-test 执行 summary 登记为数据库记录的辅助函数。
"""

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
    """测试任务视图集。
    负责面向前端提供测试任务查询、创建、失败用例查询和三类重试操作。
    """

    permission_classes = [IsAuthenticated, PlatformAccessPermission]
    serializer_class = TestRunSerializer

    def get_queryset(self):
        """构造测试任务查询集。
        Returns:
            QuerySet: 带触发用户、父任务和失败用例数量的任务查询集。
        """
        return TestRun.objects.select_related("triggered_by", "parent_run").annotate(
            failure_count=Count("failures")
        )

    def list(self, request, *args, **kwargs):
        """返回测试任务列表。
        Args:
            request: DRF 请求对象。
            *args: DRF 预留位置参数。
            **kwargs: DRF 预留关键字参数。
        Returns:
            Response: 包含 count 和 results 的任务列表。
        """
        queryset = self.get_queryset()
        return Response(
            {
                "count": queryset.count(),
                "results": self.get_serializer(queryset, many=True).data,
            }
        )

    def create(self, request, *args, **kwargs):
        """创建并执行测试任务。
        Args:
            request: DRF 请求对象，body 中包含 case_path、node_ids、retry_mode 和 retry_count。
            *args: DRF 预留位置参数。
            **kwargs: DRF 预留关键字参数。
        Returns:
            Response: 已登记的测试任务详情。
        """
        serializer = TestRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 后端只调用统一执行器并读取 summary，pytest 执行细节仍归 api-test 管理。
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
        """查询某次测试任务的失败用例。
        Args:
            request: DRF 请求对象。
            pk: 测试任务主键。
        Returns:
            Response: 包含 count 和 results 的失败用例列表。
        """
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
        """按选择的失败用例发起重试。
        Args:
            request: DRF 请求对象，body 中包含 failure_ids 和 retry_count。
            pk: 原始测试任务主键。
        Returns:
            Response: 新建重试任务详情。
        """
        original = self.get_object()
        serializer = RetrySelectedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failures = list(
            original.failures.filter(id__in=serializer.validated_data["failure_ids"])
        )

        # 选择重试以失败用例的 pytest node id 为最小执行单位。
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
        """一键重试原任务中所有失败用例。
        Args:
            request: DRF 请求对象，body 中包含 retry_count。
            pk: 原始测试任务主键。
        Returns:
            Response: 新建重试任务详情。
        """
        original = self.get_object()
        serializer = RetryCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failures = list(original.failures.filter(status=FailureCase.Status.FAILED))

        # 只重跑失败状态用例，broken/skipped 等状态保留给后续更细策略扩展。
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
        """按模块路径发起重试。
        Args:
            request: DRF 请求对象，body 中包含 module_path 和 retry_count。
            pk: 原始测试任务主键。
        Returns:
            Response: 新建模块重试任务详情。
        """
        original = self.get_object()
        serializer = RetryModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 模块重试不传 node id，让 api-test runner 按模块路径重新收集用例。
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
        """返回受控 Allure 报告入口。
        Args:
            request: DRF 请求对象。
            pk: 测试任务主键。
        Returns:
            Response: 可由前端打开的报告 URL。
        """
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
    """服务单次任务的 Allure 静态报告文件。
    Args:
        request: Django 请求对象。
        run_id: 测试任务运行 ID。
        path: 报告目录下的相对资源路径。
    Returns:
        HttpResponse: Django 静态文件响应。
    Raises:
        Http404: 任务不存在、报告不可用或路径不在受控根目录内。
    """
    test_run = TestRun.objects.filter(run_id=run_id).first()
    if not test_run or not _report_index_exists(test_run):
        raise Http404("Report is not available.")

    # 空路径统一指向 Allure 首页，保持 `/reports/<run_id>/` 可直接打开。
    safe_path = path or "index.html"
    return serve(request, safe_path, document_root=_resolve_report_dir(test_run))


def register_test_run_from_summary(
    *,
    summary: dict,
    user,
    trigger_source: str,
    parent_run: TestRun | None = None,
) -> TestRun:
    """根据 api-test summary 登记测试任务和失败用例。
    Args:
        summary: api-test runner 输出的标准执行摘要。
        user: 当前触发用户；匿名触发时可为空或未认证用户。
        trigger_source: 任务触发来源。
        parent_run: 重试任务对应的原始任务。
    Returns:
        TestRun: 已创建的测试任务记录。
    """
    now = timezone.now()

    # summary 是跨模块契约，登记时保留原始内容，便于后续排查执行器输出。
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
    """判断测试任务是否存在可打开的 Allure 首页。
    Args:
        test_run: 测试任务记录。
    Returns:
        bool: True 表示报告目录合法且包含 index.html。
    """
    report_dir = _resolve_report_dir(test_run)
    if report_dir is None:
        return False
    return (report_dir / "index.html").is_file()


def _resolve_report_dir(test_run: TestRun) -> Path | None:
    """解析并校验测试任务报告目录。
    Args:
        test_run: 测试任务记录。
    Returns:
        Path | None: 位于 ALLURE_REPORTS_ROOT 下的报告目录；非法时返回 None。
    """
    if not test_run.report_path:
        return None
    report_dir = Path(test_run.report_path).resolve()
    report_root = Path(settings.ALLURE_REPORTS_ROOT).resolve()
    try:
        # 限制报告只能来自配置根目录，避免 report_path 暴露任意服务器文件。
        report_dir.relative_to(report_root)
    except ValueError:
        return None
    return report_dir


def _record_failure_cases(test_run: TestRun, summary: dict) -> None:
    """从执行摘要中登记失败用例。
    Args:
        test_run: 已创建的测试任务记录。
        summary: api-test runner 输出的标准执行摘要。
    """
    failures = []
    allure_results_dir = summary.get("allure_results_dir")
    if allure_results_dir:
        # 优先使用 Allure 原始结果，可获得更完整的错误类型、描述和断言信息。
        failures = parse_allure_failures(Path(allure_results_dir))
    if not failures:
        # Allure 结果缺失时退回 summary.failed_nodeids，保证重试入口仍有最小数据。
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
    """根据 pytest node id 构造最小失败用例摘要。
    Args:
        node_id: pytest 原始 node id。
    Returns:
        dict: FailureCase 创建所需的最小字段。
    """
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
    """从执行摘要中推导测试任务状态。
    Args:
        summary: api-test runner 输出的标准执行摘要。
    Returns:
        str: TestRun.Status 中的合法状态值。
    """
    status_value = summary.get("status")
    if status_value in TestRun.Status.values:
        return status_value
    return TestRun.Status.PASSED if summary.get("return_code") == 0 else TestRun.Status.FAILED


def _mark_retry_result(failures: list[FailureCase], retry_run: TestRun) -> None:
    """回写失败用例的最近一次重试结果。
    Args:
        failures: 本次参与重试的原始失败用例列表。
        retry_run: 新创建的重试任务。
    """
    retry_status = (
        FailureCase.RetryStatus.PASSED
        if retry_run.status == TestRun.Status.PASSED
        else FailureCase.RetryStatus.FAILED
    )
    for failure in failures:
        # 只更新重试相关字段，避免覆盖失败用例原始错误信息。
        failure.retry_status = retry_status
        failure.last_retry_run = retry_run
        failure.save(update_fields=["retry_status", "last_retry_run", "updated_at"])
