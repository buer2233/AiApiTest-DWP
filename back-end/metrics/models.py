from __future__ import annotations

import hashlib
import uuid
from urllib.parse import urlparse

from django.db import models

from accounts.models import UserAccount


def normalize_environment_base_url(value: str) -> str:
    """校验环境 URL 并统一去除尾部斜杠，避免同一地址重复入库。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("环境 base_url 不能为空。")
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("环境 base_url 必须包含协议和域名。")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("环境 base_url 不能包含凭据。")
    return normalized


class TestEnvironment(models.Model):
    env_key = models.CharField(max_length=64, unique=True)
    env_name = models.CharField(max_length=128, db_index=True)
    base_url = models.CharField(max_length=512)
    # 为既有环境补充安全默认描述，后续目录和 API 校验仍要求传入非空描述。
    url_desc = models.TextField(default="未提供环境描述")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_environment"
        constraints = [
            models.UniqueConstraint(fields=["base_url"], name="uniq_test_environment_base_url"),
        ]
        ordering = ["env_name", "id"]

    def __str__(self) -> str:
        return self.env_name

    def save(self, *args, **kwargs):
        self.base_url = normalize_environment_base_url(self.base_url)
        super().save(*args, **kwargs)


class TestModule(models.Model):
    package_name = models.CharField(max_length=128, unique=True)
    case_path = models.CharField(max_length=512, db_index=True)
    module_name = models.CharField(max_length=128, db_index=True)
    module_dev = models.CharField(max_length=128, db_index=True)
    module_test = models.CharField(max_length=128, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_module"
        ordering = ["package_name", "id"]

    def __str__(self) -> str:
        return f"{self.package_name}:{self.module_name}"


class TestRun(models.Model):
    class RunType(models.TextChoices):
        DAILY_FULL = "daily_full", "每日全量"
        MODULE_RERUN = "module_rerun", "模块重试"
        FAILED_RERUN = "failed_rerun", "失败重试"

    class Status(models.TextChoices):
        QUEUED = "queued", "排队中"
        RUNNING = "running", "执行中"
        SUCCESS = "success", "成功"
        TEST_FAILED = "test_failed", "用例失败"
        FAILED = "failed", "失败"
        CANCELING = "canceling", "取消中"
        CANCELED = "canceled", "已取消"

    run_key = models.CharField(max_length=128, unique=True)
    run_type = models.CharField(max_length=32, choices=RunType.choices, db_index=True)
    environment = models.ForeignKey(TestEnvironment, on_delete=models.PROTECT, db_index=True)
    module = models.ForeignKey(TestModule, null=True, blank=True, on_delete=models.PROTECT, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    summary_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_run"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(run_type="daily_full") | models.Q(module__isnull=False),
                name="test_run_module_required_except_daily_full",
            ),
        ]
        ordering = ["-started_at", "-id"]

    def __str__(self) -> str:
        return self.run_key


class EnvironmentSnapshot(models.Model):
    environment = models.OneToOneField(TestEnvironment, on_delete=models.CASCADE, related_name="snapshot")
    latest_run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    passed_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    pass_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "environment_snapshot"
        ordering = ["environment_id"]

    def __str__(self) -> str:
        return f"{self.environment_id}:{self.pass_rate}"


class ModuleSnapshot(models.Model):
    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.CASCADE, db_index=True)
    latest_run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0, db_index=True)
    passed_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    pass_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "module_snapshot"
        constraints = [
            models.UniqueConstraint(fields=["environment", "module"], name="uniq_module_snapshot_environment_module"),
        ]
        ordering = ["pass_rate", "-completed_at", "id"]

    def __str__(self) -> str:
        return f"{self.environment_id}:{self.module_id}:{self.pass_rate}"


class TestCaseResult(models.Model):
    """模块快照下的单条 pytest 用例结果。"""

    class ExecutionStatus(models.TextChoices):
        PASSED = "passed", "通过"
        FAILED = "failed", "失败"
        SKIPPED = "skipped", "跳过"
        ERROR = "error", "错误"

    class DisplayStatus(models.TextChoices):
        FAILED = "failed", "失败"
        PASSED = "passed", "通过"
        SKIPPED = "skipped", "跳过"
        ARCHIVED = "archived", "已归档"

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.CASCADE, db_index=True)
    module_snapshot = models.ForeignKey(ModuleSnapshot, on_delete=models.CASCADE, related_name="case_results", db_index=True)
    source_run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    node_id = models.CharField(max_length=1024)
    current_node_key = models.CharField(max_length=64, null=True, blank=True, editable=False)
    case_name = models.CharField(max_length=256, db_index=True)
    case_summary = models.CharField(max_length=512, blank=True)
    assertion_text = models.TextField(blank=True)
    error_type = models.CharField(max_length=128, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    error_message_summary = models.CharField(max_length=512, blank=True)
    execution_status = models.CharField(max_length=32, choices=ExecutionStatus.choices, db_index=True)
    display_status = models.CharField(
        max_length=32,
        choices=DisplayStatus.choices,
        default=DisplayStatus.FAILED,
        db_index=True,
    )
    confirmation_result = models.CharField(max_length=128, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    occurred_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_case_result"
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "module", "current_node_key"],
                name="uniq_current_case_result_env_module_node",
            ),
        ]
        indexes = [
            models.Index(fields=["environment", "module", "display_status"], name="idx_case_env_module_status"),
            models.Index(fields=["module_snapshot", "is_current", "display_status"], name="idx_case_snapshot_current"),
        ]
        ordering = ["display_status", "-occurred_at", "id"]

    def __str__(self) -> str:
        return f"{self.module_id}:{self.case_name}:{self.display_status}"

    def save(self, *args, **kwargs):
        # MySQL 不支持 partial unique index；用定长哈希避免 utf8mb4 唯一索引超长。
        self.current_node_key = hashlib.sha256(self.node_id.encode("utf-8")).hexdigest() if self.is_current else None
        super().save(*args, **kwargs)


class ModuleRunHistory(models.Model):
    """模块按天沉淀的趋势数据，供 P3 趋势弹窗只读查询。"""

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.CASCADE, db_index=True)
    source_run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    run_date = models.DateField(db_index=True)
    run_type = models.CharField(max_length=32, choices=TestRun.RunType.choices, default=TestRun.RunType.DAILY_FULL, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    passed_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    pass_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "module_run_history"
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "module", "run_date", "run_type", "source_run"],
                name="uniq_module_history_env_module_date_run",
            ),
        ]
        ordering = ["run_date", "id"]

    def __str__(self) -> str:
        return f"{self.environment_id}:{self.module_id}:{self.run_date}:{self.pass_rate}"


class CaseStatusAudit(models.Model):
    """管理人员手动修改用例展示状态时写入的审计记录。"""

    case_result = models.ForeignKey(TestCaseResult, on_delete=models.PROTECT, related_name="status_audits", db_index=True)
    environment = models.ForeignKey(TestEnvironment, on_delete=models.PROTECT, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.PROTECT, db_index=True)
    changed_by = models.ForeignKey(UserAccount, on_delete=models.PROTECT, related_name="case_status_audits", db_index=True)
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    reason = models.CharField(max_length=512)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "case_status_audit"
        ordering = ["-changed_at", "-id"]

    def __str__(self) -> str:
        return f"{self.case_result_id}:{self.from_status}->{self.to_status}"


class JenkinsJobBinding(models.Model):
    """测试环境、模块和任务类型到 Jenkins Job 的映射。"""

    environment = models.ForeignKey(TestEnvironment, null=True, blank=True, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, null=True, blank=True, on_delete=models.CASCADE, db_index=True)
    task_type = models.CharField(max_length=32, choices=TestRun.RunType.choices, db_index=True)
    job_full_name = models.CharField(max_length=255, db_index=True)
    default_retry_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jenkins_job_binding"
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "module", "task_type"],
                name="uniq_jenkins_job_binding_env_module_type",
            ),
            models.CheckConstraint(
                condition=models.Q(task_type=TestRun.RunType.DAILY_FULL)
                | (models.Q(environment__isnull=False) & models.Q(module__isnull=False)),
                name="jenkins_binding_context_required_except_daily_full",
            ),
        ]
        ordering = ["environment_id", "module_id", "task_type"]

    def __str__(self) -> str:
        return f"{self.environment_id}:{self.module_id}:{self.task_type}:{self.job_full_name}"


class JenkinsTask(models.Model):
    """平台侧 Jenkins 任务记录，用于触发、取消、同步和报告入口展示。"""

    class TriggerSource(models.TextChoices):
        PLATFORM_USER = "platform_user", "平台用户"
        JENKINS_CRON = "jenkins_cron", "Jenkins 定时"
        MANUAL_SYNC = "manual_sync", "手动同步"

    run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    environment = models.ForeignKey(TestEnvironment, on_delete=models.PROTECT, db_index=True)
    module = models.ForeignKey(TestModule, null=True, blank=True, on_delete=models.PROTECT, db_index=True)
    task_type = models.CharField(max_length=32, choices=TestRun.RunType.choices, db_index=True)
    trigger_source = models.CharField(max_length=32, choices=TriggerSource.choices, default=TriggerSource.PLATFORM_USER, db_index=True)
    triggered_by = models.ForeignKey(UserAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="jenkins_tasks", db_index=True)
    job_full_name = models.CharField(max_length=255, db_index=True)
    queue_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    build_number = models.IntegerField(null=True, blank=True)
    jenkins_queue_url = models.CharField(max_length=1024, blank=True)
    jenkins_build_url = models.CharField(max_length=1024, blank=True)
    artifact_base_url = models.CharField(max_length=1024, blank=True)
    summary_artifact_url = models.CharField(max_length=1024, blank=True)
    failed_nodeids_artifact_url = models.CharField(max_length=1024, blank=True)
    allure_report_url = models.CharField(max_length=1024, blank=True)
    status = models.CharField(max_length=32, choices=TestRun.Status.choices, default=TestRun.Status.QUEUED, db_index=True)
    jenkins_result = models.CharField(max_length=64, blank=True)
    requested_nodeids_json = models.JSONField(default=list, blank=True)
    summary_json = models.JSONField(null=True, blank=True)
    failed_nodeids_json = models.JSONField(default=list, blank=True)
    error_summary = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_synced_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jenkins_task"
        constraints = [
            models.UniqueConstraint(
                fields=["job_full_name", "build_number"],
                name="uniq_jenkins_task_job_build",
            ),
            models.CheckConstraint(
                condition=models.Q(task_type=TestRun.RunType.DAILY_FULL) | models.Q(module__isnull=False),
                name="jenkins_task_module_required_except_daily_full",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.job_full_name}#{self.build_number or self.queue_id or self.id}"


class EnvironmentCatalogState(models.Model):
    """唯一的环境目录状态投影，不以仓库 HEAD 代替 YAML blob SHA。"""

    CATALOG_KEY = "package_environment"

    class Status(models.TextChoices):
        SYNCED = "synced", "已同步"
        PENDING = "pending", "待同步"
        QUEUED = "queued", "已排队"
        RUNNING = "running", "同步中"
        CONFLICT = "conflict", "冲突"
        FAILED = "failed", "失败"

    catalog_key = models.CharField(max_length=64, unique=True, default=CATALOG_KEY)
    yaml_blob_sha = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.SYNCED, db_index=True)
    last_commit_sha = models.CharField(max_length=40, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    last_error_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "environment_catalog_state"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(catalog_key="package_environment"),
                name="environment_catalog_state_singleton_key",
            ),
        ]


def _new_catalog_request_id() -> str:
    return uuid.uuid4().hex


class EnvironmentCatalogSyncAttempt(models.Model):
    """环境 YAML 双向同步的追加审计，终态请求从不原地复用。"""

    class Direction(models.TextChoices):
        MYSQL_TO_YAML = "mysql_to_yaml", "MySQL 写回 YAML"
        YAML_TO_MYSQL = "yaml_to_mysql", "YAML 导入 MySQL"

    class Status(models.TextChoices):
        PENDING = "pending", "待同步"
        QUEUED = "queued", "已排队"
        RUNNING = "running", "同步中"
        SYNCED = "synced", "已同步"
        CONFLICT = "conflict", "冲突"
        FAILED = "failed", "失败"

    ACTIVE_STATUSES = frozenset({Status.PENDING, Status.QUEUED, Status.RUNNING})

    request_id = models.CharField(max_length=64, unique=True, default=_new_catalog_request_id, editable=False)
    direction = models.CharField(max_length=32, choices=Direction.choices, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING, db_index=True)
    expected_yaml_blob_sha = models.CharField(max_length=40, null=True, blank=True)
    observed_yaml_blob_sha = models.CharField(max_length=40, null=True, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    payload_sha256 = models.CharField(max_length=64, blank=True)
    queue_id = models.CharField(max_length=128, blank=True)
    build_number = models.IntegerField(null=True, blank=True)
    jenkins_build_url = models.CharField(max_length=1024, blank=True)
    job_full_name = models.CharField(max_length=255, default="AiApiTest-DWP-Environment-Catalog-Sync")
    commit_sha = models.CharField(max_length=40, blank=True)
    requested_by = models.ForeignKey(
        UserAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="environment_catalog_sync_attempts",
        db_index=True,
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_summary = models.TextField(blank=True)
    active_attempt_key = models.CharField(max_length=64, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "environment_catalog_sync_attempt"
        constraints = [
            models.UniqueConstraint(fields=["active_attempt_key"], name="uniq_active_environment_catalog_sync"),
            models.UniqueConstraint(
                fields=["job_full_name", "build_number"],
                name="uniq_environment_catalog_sync_job_build",
            ),
        ]
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        # MySQL 无 partial unique；活动请求使用固定键，终态释放为 NULL。
        self.active_attempt_key = EnvironmentCatalogState.CATALOG_KEY if self.status in self.ACTIVE_STATUSES else None
        super().save(*args, **kwargs)


class ModuleExecutionLock(models.Model):
    """同环境同模块的 Jenkins 执行互斥锁。"""

    class Status(models.TextChoices):
        ACTIVE = "active", "生效中"
        RELEASED = "released", "已释放"
        EXPIRED = "expired", "已过期"

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.CASCADE, db_index=True)
    task = models.ForeignKey(JenkinsTask, on_delete=models.CASCADE, related_name="execution_locks", db_index=True)
    lock_type = models.CharField(max_length=32, default="module_execution")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    active_lock_key = models.CharField(max_length=128, null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    released_at = models.DateTimeField(null=True, blank=True, db_index=True)
    release_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "module_execution_lock"
        constraints = [
            models.UniqueConstraint(fields=["active_lock_key"], name="uniq_active_module_execution_lock"),
        ]
        ordering = ["-locked_at", "-id"]

    def save(self, *args, **kwargs):
        # MySQL 无 partial unique，用可空 active_lock_key 保证只有 active 锁互斥。
        if self.status == self.Status.ACTIVE:
            self.active_lock_key = f"env:{self.environment_id}:module:{self.module_id}"
        else:
            self.active_lock_key = None
        super().save(*args, **kwargs)
