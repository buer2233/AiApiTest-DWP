from __future__ import annotations

import re

from rest_framework import serializers

from common.serializers import PaginationMetaSerializer
from metrics.models import ModuleRunHistory, ModuleSnapshot, TestCaseResult, TestEnvironment


SENSITIVE_PATTERNS = [
    (
        re.compile(
            r"https?://(?:[^/\s:@]+:[^@\s/]+@)?"
            r"(?:localhost|127(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
            r"(?::\d+)?(?:/[^\s;]*)?",
            re.IGNORECASE,
        ),
        "[REDACTED_URL]",
    ),
    (re.compile(r"(Authorization\s*:\s*Bearer\s+)[^\s;]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(password\s*[=:]\s*)[^\s;]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(cookie\s*[=:]\s*)[^\s;]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(token\s*[=:]\s*)[^\s;]+", re.IGNORECASE), r"\1[REDACTED]"),
]


def redact_sensitive_text(value: str) -> str:
    # 后端只返回脱敏后的错误详情，避免 token/cookie 等调试信息进入前端。
    redacted = value
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


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
            "trend_7d": True,
            "trend_30d": True,
            "jenkins_tasks": False,
        }


class ModuleSnapshotListResponseSerializer(serializers.Serializer):
    data = ModuleSnapshotSerializer(many=True)
    meta = PaginationMetaSerializer()


class CaseResultSerializer(serializers.ModelSerializer):
    error_message_detail = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseResult
        fields = [
            "id",
            "node_id",
            "case_name",
            "case_summary",
            "error_type",
            "assertion_text",
            "execution_status",
            "display_status",
            "error_message_summary",
            "error_message_detail",
            "confirmation_result",
            "actions",
        ]

    def get_error_message_detail(self, obj: TestCaseResult) -> str | None:
        if not self.context.get("can_view_error_detail"):
            return None
        return redact_sensitive_text(obj.error_message)

    def get_actions(self, obj: TestCaseResult) -> dict[str, bool]:
        return {
            "can_update_status": bool(self.context.get("can_update_status")),
            "can_retry": False,
        }


class CaseResultListResponseSerializer(serializers.Serializer):
    data = CaseResultSerializer(many=True)
    meta = PaginationMetaSerializer()


class CaseStatusUpdateRequestSerializer(serializers.Serializer):
    display_status = serializers.ChoiceField(choices=["failed", "passed", "skipped"])
    reason = serializers.CharField(min_length=1, max_length=512, trim_whitespace=True)


class CaseStatusCaseResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_status = serializers.CharField()
    confirmation_result = serializers.CharField()


class ModuleStatusSummarySerializer(serializers.Serializer):
    snapshot_id = serializers.IntegerField()
    total_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    passed_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    pass_rate = serializers.DecimalField(max_digits=8, decimal_places=6)


class EnvironmentStatusSummarySerializer(serializers.Serializer):
    environment_id = serializers.IntegerField()
    total_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    pass_rate = serializers.DecimalField(max_digits=8, decimal_places=6)


class CaseStatusUpdateDataSerializer(serializers.Serializer):
    case_result = CaseStatusCaseResultSerializer()
    module_summary = ModuleStatusSummarySerializer()
    environment_summary = EnvironmentStatusSummarySerializer()
    audit_id = serializers.IntegerField()


class CaseStatusUpdateResponseSerializer(serializers.Serializer):
    data = CaseStatusUpdateDataSerializer()


class TrendModuleSerializer(serializers.Serializer):
    snapshot_id = serializers.IntegerField()
    module_name = serializers.CharField()
    package_name = serializers.CharField()
    environment_name = serializers.CharField()


class ModuleRunHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleRunHistory
        fields = [
            "run_date",
            "run_type",
            "total_count",
            "failed_count",
            "skipped_count",
            "pass_rate",
            "duration_seconds",
        ]


class ModuleTrendDataSerializer(serializers.Serializer):
    module = TrendModuleSerializer()
    days = serializers.IntegerField()
    series = ModuleRunHistorySerializer(many=True)


class ModuleTrendResponseSerializer(serializers.Serializer):
    data = ModuleTrendDataSerializer()
