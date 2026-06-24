"""jenkins_integration 初始迁移。
本迁移创建 JenkinsBuildRecord，用于保存平台触发 Jenkins 构建时的审计记录。
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """创建 Jenkins 构建触发记录模型的初始迁移。"""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="JenkinsBuildRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_name", models.CharField(max_length=300)),
                ("build_number", models.PositiveIntegerField(blank=True, null=True)),
                ("queue_status", models.CharField(default="queued", max_length=50)),
                ("parameters", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="jenkins_build_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
