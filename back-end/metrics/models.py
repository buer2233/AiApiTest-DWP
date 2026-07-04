from __future__ import annotations

from django.db import models


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
        FAILED = "failed", "失败"
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
