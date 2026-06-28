from django.db import models
from django.utils import timezone


class TestCaseItem(models.Model):
    __test__ = False

    class SyncStatus(models.TextChoices):
        SYNCED = "synced", "Synced"
        MISSING = "missing", "Missing"

    node_id = models.CharField(max_length=512, unique=True)
    package_name = models.CharField(max_length=200, db_index=True)
    module_name = models.CharField(max_length=200, db_index=True)
    file_path = models.CharField(max_length=500, db_index=True)
    class_name = models.CharField(max_length=200, blank=True)
    function_name = models.CharField(max_length=200, db_index=True)
    title = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    markers = models.JSONField(default=list)
    sync_status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.SYNCED, db_index=True)
    last_synced_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_case_item"
        ordering = ["package_name", "file_path", "function_name"]

    def __str__(self) -> str:
        return self.node_id
