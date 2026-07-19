from __future__ import annotations

import hashlib
import uuid
from urllib.parse import urlparse

import django.db.models.deletion
from django.db import migrations, models


def normalize_existing_environment_urls(apps, schema_editor):
    TestEnvironment = apps.get_model("metrics", "TestEnvironment")
    seen_urls: set[str] = set()
    pending_updates: list[tuple[int, str]] = []

    # 先完成全量校验，避免后续记录非法时留下部分 URL 已写入的迁移状态。
    for environment in TestEnvironment.objects.order_by("id").iterator():
        normalized_url = environment.base_url.strip().rstrip("/")
        parsed = urlparse(normalized_url)
        if not parsed.scheme or not parsed.netloc or parsed.username is not None or parsed.password is not None:
            raise RuntimeError(f"无法迁移非法测试环境 URL: id={environment.id}")
        if normalized_url in seen_urls:
            raise RuntimeError(f"无法迁移重复测试环境 URL: {normalized_url}")
        seen_urls.add(normalized_url)
        if environment.base_url != normalized_url:
            pending_updates.append((environment.id, normalized_url))

    for environment_id, normalized_url in pending_updates:
        TestEnvironment.objects.filter(pk=environment_id).update(base_url=normalized_url)


def new_catalog_request_id() -> str:
    return uuid.uuid4().hex


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("metrics", "0004_hash_case_result_current_node_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="testenvironment",
            name="url_desc",
            field=models.TextField(default="未提供环境描述"),
        ),
        migrations.RunPython(normalize_existing_environment_urls, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="testenvironment",
            constraint=models.UniqueConstraint(fields=("base_url",), name="uniq_test_environment_base_url"),
        ),
        migrations.AddConstraint(
            model_name="testrun",
            constraint=models.CheckConstraint(
                condition=models.Q(("run_type", "daily_full"), ("module__isnull", False), _connector="OR"),
                name="test_run_module_required_except_daily_full",
            ),
        ),
        migrations.AlterField(
            model_name="jenkinsjobbinding",
            name="environment",
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="metrics.testenvironment"),
        ),
        migrations.AlterField(
            model_name="jenkinsjobbinding",
            name="module",
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="metrics.testmodule"),
        ),
        migrations.AddConstraint(
            model_name="jenkinsjobbinding",
            constraint=models.CheckConstraint(
                condition=models.Q(("task_type", "daily_full"))
                | (models.Q(("environment__isnull", False)) & models.Q(("module__isnull", False))),
                name="jenkins_binding_context_required_except_daily_full",
            ),
        ),
        migrations.AlterField(
            model_name="jenkinstask",
            name="module",
            field=models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="metrics.testmodule"),
        ),
        migrations.AddConstraint(
            model_name="jenkinstask",
            constraint=models.CheckConstraint(
                condition=models.Q(("task_type", "daily_full"), ("module__isnull", False), _connector="OR"),
                name="jenkins_task_module_required_except_daily_full",
            ),
        ),
        migrations.CreateModel(
            name="EnvironmentCatalogState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("catalog_key", models.CharField(default="package_environment", max_length=64, unique=True)),
                ("yaml_blob_sha", models.CharField(blank=True, db_index=True, max_length=40, null=True)),
                ("status", models.CharField(choices=[("synced", "已同步"), ("pending", "待同步"), ("queued", "已排队"), ("running", "同步中"), ("conflict", "冲突"), ("failed", "失败")], db_index=True, default="synced", max_length=32)),
                ("last_commit_sha", models.CharField(blank=True, max_length=40)),
                ("last_synced_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_error_code", models.CharField(blank=True, max_length=64)),
                ("last_error_summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "environment_catalog_state"},
        ),
        migrations.AddConstraint(
            model_name="environmentcatalogstate",
            constraint=models.CheckConstraint(
                condition=models.Q(("catalog_key", "package_environment")),
                name="environment_catalog_state_singleton_key",
            ),
        ),
        migrations.CreateModel(
            name="EnvironmentCatalogSyncAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_id", models.CharField(default=new_catalog_request_id, editable=False, max_length=64, unique=True)),
                ("direction", models.CharField(choices=[("mysql_to_yaml", "MySQL 写回 YAML"), ("yaml_to_mysql", "YAML 导入 MySQL")], db_index=True, max_length=32)),
                ("status", models.CharField(choices=[("pending", "待同步"), ("queued", "已排队"), ("running", "同步中"), ("synced", "已同步"), ("conflict", "冲突"), ("failed", "失败")], db_index=True, default="pending", max_length=32)),
                ("expected_yaml_blob_sha", models.CharField(blank=True, max_length=40, null=True)),
                ("observed_yaml_blob_sha", models.CharField(blank=True, max_length=40, null=True)),
                ("payload_json", models.JSONField(blank=True, default=dict)),
                ("payload_sha256", models.CharField(blank=True, max_length=64)),
                ("queue_id", models.CharField(blank=True, max_length=128)),
                ("build_number", models.IntegerField(blank=True, null=True)),
                ("jenkins_build_url", models.CharField(blank=True, max_length=1024)),
                ("job_full_name", models.CharField(default="AiApiTest-DWP-Environment-Catalog-Sync", max_length=255)),
                ("commit_sha", models.CharField(blank=True, max_length=40)),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("error_summary", models.TextField(blank=True)),
                ("active_attempt_key", models.CharField(blank=True, editable=False, max_length=64, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("finished_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_by", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="environment_catalog_sync_attempts", to="accounts.useraccount")),
            ],
            options={"db_table": "environment_catalog_sync_attempt", "ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="environmentcatalogsyncattempt",
            constraint=models.UniqueConstraint(fields=("active_attempt_key",), name="uniq_active_environment_catalog_sync"),
        ),
        migrations.AddConstraint(
            model_name="environmentcatalogsyncattempt",
            constraint=models.UniqueConstraint(fields=("job_full_name", "build_number"), name="uniq_environment_catalog_sync_job_build"),
        ),
    ]
