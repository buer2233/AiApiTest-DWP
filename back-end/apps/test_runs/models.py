"""测试任务与失败用例模型模块。
本模块保存一次接口自动化执行的任务摘要、报告路径、触发来源和失败用例明细。
后端、前端和 Jenkins 集成都围绕这些模型展示执行结果、发起重试和打开 Allure 报告。
"""

from django.conf import settings
from django.db import models


class TestRun(models.Model):
    """接口自动化测试任务记录。
    一条记录对应一次 pytest/CI 执行，包含执行参数、状态、产物路径、触发人和重试父任务。
    """

    # 避免 pytest 把 Django 模型类误识别为测试类。
    __test__ = False

    class RetryMode(models.TextChoices):
        """测试任务重试模式。"""

        NONE = "none", "None"
        SELECTED = "selected", "Selected"
        ALL_FAILED = "all-failed", "All Failed"
        MODULE = "module", "Module"

    class Status(models.TextChoices):
        """测试任务执行状态。"""

        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        ERROR = "error", "Error"

    class TriggerSource(models.TextChoices):
        """测试任务触发来源。"""

        API = "api", "API"
        JENKINS = "jenkins", "Jenkins"
        MANUAL = "manual", "Manual"

    run_id = models.CharField(max_length=120, unique=True)
    case_path = models.CharField(max_length=500)
    node_ids = models.JSONField(default=list, blank=True)
    retry_mode = models.CharField(
        max_length=20,
        choices=RetryMode.choices,
        default=RetryMode.NONE,
    )
    retry_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="test_runs",
    )
    trigger_source = models.CharField(
        max_length=20,
        choices=TriggerSource.choices,
        default=TriggerSource.API,
    )
    parent_run = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retry_runs",
    )
    report_path = models.CharField(max_length=1000, blank=True)
    allure_results_path = models.CharField(max_length=1000, blank=True)
    console_log_path = models.CharField(max_length=1000, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """测试任务默认按最新创建时间倒序展示。"""

        ordering = ["-created_at", "-id"]

    def __str__(self):
        """返回任务唯一运行 ID，便于 Django admin 和日志展示。"""
        return self.run_id


class FailureCase(models.Model):
    """失败用例记录。
    一条记录对应某次测试任务中的一个失败或 broken 用例，保存 pytest node id 和重试状态。
    """

    # 避免 pytest 把 Django 模型类误识别为测试类。
    __test__ = False

    class Status(models.TextChoices):
        """Allure/pytest 失败用例状态。"""

        FAILED = "failed", "Failed"
        BROKEN = "broken", "Broken"
        SKIPPED = "skipped", "Skipped"
        UNKNOWN = "unknown", "Unknown"

    class RetryStatus(models.TextChoices):
        """失败用例后续重试结果。"""

        NOT_RETRIED = "not-retried", "Not Retried"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE,
        related_name="failures",
    )
    node_id = models.CharField(max_length=1000)
    case_name = models.CharField(max_length=500)
    module_path = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    error_type = models.CharField(max_length=200, blank=True)
    assertion_message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FAILED,
    )
    retry_status = models.CharField(
        max_length=20,
        choices=RetryStatus.choices,
        default=RetryStatus.NOT_RETRIED,
    )
    last_retry_run = models.ForeignKey(
        TestRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retried_failures",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """失败用例按创建顺序稳定展示，方便前端列表和测试断言。"""

        ordering = ["id"]

    def __str__(self):
        """返回 pytest node id，便于定位失败用例。"""
        return self.node_id
