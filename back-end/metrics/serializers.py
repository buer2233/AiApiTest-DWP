from __future__ import annotations

from rest_framework import serializers

from common.serializers import PaginationMetaSerializer
from metrics.models import ModuleSnapshot, TestEnvironment


class TestEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestEnvironment
        fields = ["id", "env_key", "env_name", "base_url"]


class EnvironmentSummarySerializer(serializers.Serializer):
    environment = TestEnvironmentSerializer()
    started_at = serializers.DateTimeField(allow_null=True)
    finished_at = serializers.DateTimeField(allow_null=True)
    duration_seconds = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    total_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    passed_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    pass_rate = serializers.DecimalField(max_digits=8, decimal_places=6)
    actions = serializers.DictField(child=serializers.BooleanField())


class EnvironmentSummaryResponseSerializer(serializers.Serializer):
    data = EnvironmentSummarySerializer()


class TestEnvironmentListResponseSerializer(serializers.Serializer):
    data = TestEnvironmentSerializer(many=True)


class ModuleSnapshotSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="module.package_name")
    module_name = serializers.CharField(source="module.module_name")
    module_dev = serializers.CharField(source="module.module_dev")
    module_test = serializers.CharField(source="module.module_test")
    actions = serializers.SerializerMethodField()

    class Meta:
        model = ModuleSnapshot
        fields = [
            "id",
            "completed_at",
            "package_name",
            "module_name",
            "module_dev",
            "module_test",
            "total_count",
            "failed_count",
            "skipped_count",
            "pass_rate",
            "duration_seconds",
            "actions",
        ]

    def get_actions(self, obj: ModuleSnapshot) -> dict[str, bool]:
        return {
            "failed_rerun": False,
            "module_rerun": False,
            "trend_7d": False,
            "trend_30d": False,
            "jenkins_tasks": False,
        }


class ModuleSnapshotListResponseSerializer(serializers.Serializer):
    data = ModuleSnapshotSerializer(many=True)
    meta = PaginationMetaSerializer()
