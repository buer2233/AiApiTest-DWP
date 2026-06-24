"""Jenkins 构建记录模型模块。
本模块保存后端触发 Jenkins 参数化构建时的请求记录，便于平台展示和后续审计。
真实 build 详情仍通过 Jenkins API 查询，不在本地重复同步完整 Jenkins 数据。
"""

from django.conf import settings
from django.db import models


class JenkinsBuildRecord(models.Model):
    """Jenkins 构建触发记录。
    记录触发的 job、队列状态、触发用户和传给 Jenkinsfile 的参数。
    """

    job_name = models.CharField(max_length=300)
    build_number = models.PositiveIntegerField(null=True, blank=True)
    queue_status = models.CharField(max_length=50, default="queued")
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="jenkins_build_records",
    )
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """构建记录默认按最新触发时间倒序展示。"""

        ordering = ["-created_at", "-id"]

