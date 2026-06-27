"""testcases 序列化器。"""
from rest_framework import serializers

from .models import TestCaseSnapshot


class TestCaseSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseSnapshot
        fields = [
            "id",
            "module_key",
            "module_name",
            "case_path",
            "node_id",
            "function_name",
            "class_name",
            "case_title",
            "story",
            "severity",
            "is_active",
            "synced_at",
        ]
