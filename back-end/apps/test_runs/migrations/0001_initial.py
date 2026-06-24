"""test_runs 初始迁移。
本迁移创建测试任务 TestRun 和失败用例 FailureCase 两张核心业务表。
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """创建测试任务与失败用例模型的初始迁移。"""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TestRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_id", models.CharField(max_length=120, unique=True)),
                ("case_path", models.CharField(max_length=500)),
                ("node_ids", models.JSONField(blank=True, default=list)),
                (
                    "retry_mode",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("selected", "Selected"),
                            ("all-failed", "All Failed"),
                            ("module", "Module"),
                        ],
                        default="none",
                        max_length=20,
                    ),
                ),
                ("retry_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                            ("error", "Error"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "trigger_source",
                    models.CharField(
                        choices=[
                            ("api", "API"),
                            ("jenkins", "Jenkins"),
                            ("manual", "Manual"),
                        ],
                        default="api",
                        max_length=20,
                    ),
                ),
                ("report_path", models.CharField(blank=True, max_length=1000)),
                ("allure_results_path", models.CharField(blank=True, max_length=1000)),
                ("console_log_path", models.CharField(blank=True, max_length=1000)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="retry_runs",
                        to="test_runs.testrun",
                    ),
                ),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="test_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="FailureCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_id", models.CharField(max_length=1000)),
                ("case_name", models.CharField(max_length=500)),
                ("module_path", models.CharField(max_length=500)),
                ("description", models.TextField(blank=True)),
                ("error_type", models.CharField(blank=True, max_length=200)),
                ("assertion_message", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("failed", "Failed"),
                            ("broken", "Broken"),
                            ("skipped", "Skipped"),
                            ("unknown", "Unknown"),
                        ],
                        default="failed",
                        max_length=20,
                    ),
                ),
                (
                    "retry_status",
                    models.CharField(
                        choices=[
                            ("not-retried", "Not Retried"),
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                        ],
                        default="not-retried",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "last_retry_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="retried_failures",
                        to="test_runs.testrun",
                    ),
                ),
                (
                    "test_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="failures",
                        to="test_runs.testrun",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
