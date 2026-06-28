from rest_framework import serializers

from apps.testcases.models import TestCaseItem


class TestCaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseItem
        fields = (
            "id",
            "node_id",
            "package_name",
            "module_name",
            "file_path",
            "class_name",
            "function_name",
            "title",
            "description",
            "markers",
            "sync_status",
            "last_synced_at",
            "created_at",
            "updated_at",
        )
