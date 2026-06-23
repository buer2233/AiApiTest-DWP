from django.conf import settings
from django.db import models


class TestRun(models.Model):
    __test__ = False

    class RetryMode(models.TextChoices):
        NONE = "none", "None"
        SELECTED = "selected", "Selected"
        ALL_FAILED = "all-failed", "All Failed"
        MODULE = "module", "Module"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        ERROR = "error", "Error"

    class TriggerSource(models.TextChoices):
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
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.run_id


class FailureCase(models.Model):
    __test__ = False

    class Status(models.TextChoices):
        FAILED = "failed", "Failed"
        BROKEN = "broken", "Broken"
        SKIPPED = "skipped", "Skipped"
        UNKNOWN = "unknown", "Unknown"

    class RetryStatus(models.TextChoices):
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
        ordering = ["id"]

    def __str__(self):
        return self.node_id
