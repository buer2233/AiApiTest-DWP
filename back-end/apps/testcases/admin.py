from django.contrib import admin

from apps.testcases.models import TestCaseItem


@admin.register(TestCaseItem)
class TestCaseItemAdmin(admin.ModelAdmin):
    list_display = ("package_name", "module_name", "function_name", "sync_status", "last_synced_at")
    list_filter = ("package_name", "sync_status")
    search_fields = ("node_id", "function_name", "title", "description")
