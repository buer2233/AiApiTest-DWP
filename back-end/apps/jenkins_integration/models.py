from django.conf import settings
from django.db import models


class JenkinsBuildRecord(models.Model):
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
        ordering = ["-created_at", "-id"]

