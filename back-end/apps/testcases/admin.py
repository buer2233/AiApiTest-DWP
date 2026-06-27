"""testcases 后台：用例快照只读查看。"""
from django.contrib import admin

from .models import TestCaseSnapshot


@admin.register(TestCaseSnapshot)
class TestCaseSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "module_key",
        "case_title",
        "node_id",
        "story",
        "severity",
        "is_active",
        "synced_at",
    )
    list_filter = ("module_key", "is_active", "severity")
    search_fields = ("node_id", "case_title", "function_name")
    readonly_fields = ("created_at", "updated_at", "synced_at")
