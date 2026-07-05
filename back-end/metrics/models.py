from __future__ import annotations

from django.db import models

from accounts.models import UserAccount


class TestEnvironment(models.Model):
    env_key = models.CharField(max_length=64, unique=True)
    env_name = models.CharField(max_length=128, db_index=True)
    base_url = models.CharField(max_length=512)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_environment"
        ordering = ["env_name", "id"]

    def __str__(self) -> str:
        return self.env_name


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
    node_id = models.CharField(max_length=1024, db_index=True)
    current_node_key = models.CharField(max_length=1024, null=True, blank=True, editable=False)
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
        # MySQL 不支持 partial unique index，用可空 current_node_key 达成“当前用例唯一、历史可重复”。
        self.current_node_key = self.node_id if self.is_current else None
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

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, db_index=True)
    module = models.ForeignKey(TestModule, on_delete=models.CASCADE, db_index=True)
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
    module = models.ForeignKey(TestModule, on_delete=models.PROTECT, db_index=True)
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
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.job_full_name}#{self.build_number or self.queue_id or self.id}"


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
