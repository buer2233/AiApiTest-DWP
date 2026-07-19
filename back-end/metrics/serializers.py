from __future__ import annotations

import os
import re
import urllib.parse

from rest_framework import serializers

from common.serializers import PaginationMetaSerializer
from metrics.models import (
    EnvironmentCatalogState,
    EnvironmentCatalogSyncAttempt,
    JenkinsJobBinding,
    JenkinsTask,
    ModuleExecutionLock,
    ModuleRunHistory,
    ModuleSnapshot,
    TestCaseResult,
    TestEnvironment,
)


ACTIVE_TASK_STATUSES = {"queued", "running", "canceling"}
RERUN_TASK_TYPES = {"failed_rerun", "module_rerun"}


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


class EnvironmentCatalogEnvironmentSerializer(serializers.ModelSerializer):
    """Stage13 环境管理接口使用 YAML 同名字段，同时保留旧 env_name 兼容字段。"""

    url_name = serializers.CharField(source="env_name")

    class Meta:
        model = TestEnvironment
        fields = ["id", "env_key", "env_name", "url_name", "base_url", "url_desc", "is_active"]


class StrictFieldsSerializer(serializers.Serializer):
    """拒绝 DRF 默认忽略的未知字段，避免环境配置被悄然丢弃。"""

    def validate(self, attrs):
        unknown_fields = set(self.initial_data) - set(self.fields)
        if unknown_fields:
            raise serializers.ValidationError("请求包含未允许字段。")
        return super().validate(attrs)


class TestEnvironmentCreateRequestSerializer(StrictFieldsSerializer):
    env_key = serializers.CharField(min_length=1, max_length=64, trim_whitespace=True)
    url_name = serializers.CharField(min_length=1, max_length=128, trim_whitespace=True)
    base_url = serializers.CharField(min_length=1, max_length=512, trim_whitespace=True)
    url_desc = serializers.CharField(min_length=1, trim_whitespace=True)


class TestEnvironmentUpdateRequestSerializer(StrictFieldsSerializer):
    url_name = serializers.CharField(min_length=1, max_length=128, trim_whitespace=True, required=False)
    base_url = serializers.CharField(min_length=1, max_length=512, trim_whitespace=True, required=False)
    url_desc = serializers.CharField(min_length=1, trim_whitespace=True, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs:
            raise serializers.ValidationError("至少提供一个可更新字段。")
        return attrs


class EnvironmentCatalogStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentCatalogState
        fields = [
            "status",
            "yaml_blob_sha",
            "last_commit_sha",
            "last_synced_at",
            "last_error_code",
            "last_error_summary",
        ]


class EnvironmentCatalogSyncAttemptSerializer(serializers.ModelSerializer):
    requested_by = serializers.CharField(source="requested_by.display_name", allow_null=True)

    class Meta:
        model = EnvironmentCatalogSyncAttempt
        fields = [
            "id",
            "request_id",
            "direction",
            "status",
            "expected_yaml_blob_sha",
            "observed_yaml_blob_sha",
            "queue_id",
            "build_number",
            "jenkins_build_url",
            "job_full_name",
            "commit_sha",
            "requested_by",
            "error_code",
            "error_summary",
            "created_at",
            "finished_at",
        ]


class EnvironmentCatalogWriteResponseSerializer(serializers.Serializer):
    environment = EnvironmentCatalogEnvironmentSerializer()
    sync_attempt = EnvironmentCatalogSyncAttemptSerializer()


class EnvironmentCatalogWriteEnvelopeSerializer(serializers.Serializer):
    data = EnvironmentCatalogWriteResponseSerializer()


class EnvironmentCatalogSyncAttemptResponseSerializer(serializers.Serializer):
    data = EnvironmentCatalogSyncAttemptSerializer()


class EnvironmentCatalogListResponseSerializer(serializers.Serializer):
    data = EnvironmentCatalogEnvironmentSerializer(many=True)
    catalog_state = EnvironmentCatalogStateSerializer()


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
    disabled_reasons = serializers.SerializerMethodField()

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
            "disabled_reasons",
        ]

    def _action_state(self, obj: ModuleSnapshot) -> dict:
        request = self.context.get("request")
        is_admin_user = getattr(getattr(request, "user", None), "role", None) == "admin"
        has_failed_binding = JenkinsJobBinding.objects.filter(
            environment=obj.environment,
            module=obj.module,
            task_type="failed_rerun",
            is_active=True,
        ).exists()
        has_module_binding = JenkinsJobBinding.objects.filter(
            environment=obj.environment,
            module=obj.module,
            task_type="module_rerun",
            is_active=True,
        ).exists()
        has_active_lock = ModuleExecutionLock.objects.filter(
            environment=obj.environment,
            module=obj.module,
            status=ModuleExecutionLock.Status.ACTIVE,
        ).exists()
        has_active_rerun_task = JenkinsTask.objects.filter(
            environment=obj.environment,
            module=obj.module,
            task_type__in=RERUN_TASK_TYPES,
            status__in=ACTIVE_TASK_STATUSES,
        ).exists()
        has_tasks = JenkinsTask.objects.filter(environment=obj.environment, module=obj.module).exists()
        return {
            "is_admin_user": is_admin_user,
            "has_failed_binding": has_failed_binding,
            "has_module_binding": has_module_binding,
            "has_active_lock": has_active_lock,
            "has_active_rerun_task": has_active_rerun_task,
            "has_tasks": has_tasks,
        }

    def get_actions(self, obj: ModuleSnapshot) -> dict[str, bool]:
        state = self._action_state(obj)
        return {
            "failed_rerun": (
                state["is_admin_user"]
                and state["has_failed_binding"]
                and obj.failed_count > 0
            ),
            "module_rerun": state["is_admin_user"] and state["has_module_binding"],
            "trend_7d": True,
            "trend_30d": True,
            "jenkins_tasks": state["has_tasks"] or state["has_failed_binding"] or state["has_module_binding"],
        }

    def get_disabled_reasons(self, obj: ModuleSnapshot) -> dict[str, str]:
        state = self._action_state(obj)
        reasons: dict[str, str] = {}
        if not state["is_admin_user"]:
            reasons["failed_rerun"] = "无权限"
            reasons["module_rerun"] = "无权限"
            return reasons
        if not state["has_failed_binding"]:
            reasons["failed_rerun"] = "Jenkins Job 未配置"
        elif obj.failed_count <= 0:
            reasons["failed_rerun"] = "无失败用例"
        elif state["has_active_lock"] or state["has_active_rerun_task"]:
            reasons["failed_rerun"] = "已有执行中任务"
        if not state["has_module_binding"]:
            reasons["module_rerun"] = "Jenkins Job 未配置"
        elif state["has_active_lock"] or state["has_active_rerun_task"]:
            reasons["module_rerun"] = "已有执行中任务"
        return reasons


class ModuleSnapshotListResponseSerializer(serializers.Serializer):
    data = ModuleSnapshotSerializer(many=True)
    meta = PaginationMetaSerializer()


class FilterOptionSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    count = serializers.IntegerField()


class ModuleSnapshotFilterOptionsDataSerializer(serializers.Serializer):
    module_names = FilterOptionSerializer(many=True)
    package_names = FilterOptionSerializer(many=True)
    module_devs = FilterOptionSerializer(many=True)
    module_tests = FilterOptionSerializer(many=True)


class ModuleSnapshotFilterOptionsResponseSerializer(serializers.Serializer):
    data = ModuleSnapshotFilterOptionsDataSerializer()


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
        has_retry_binding = JenkinsJobBinding.objects.filter(
            environment=obj.environment,
            module=obj.module,
            task_type="failed_rerun",
            is_active=True,
        ).exists()
        return {
            "can_update_status": bool(self.context.get("can_update_status")),
            "can_retry": (
                bool(self.context.get("can_update_status"))
                and obj.is_current
                and obj.display_status == TestCaseResult.DisplayStatus.FAILED
                and has_retry_binding
            ),
        }


class JenkinsTaskSerializer(serializers.ModelSerializer):
    job_name = serializers.SerializerMethodField()
    environment_url = serializers.CharField(source="environment.base_url")
    triggered_by = serializers.SerializerMethodField()
    jenkins_build_url = serializers.SerializerMethodField()
    allure_report_url = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = JenkinsTask
        fields = [
            "id",
            "task_type",
            "job_name",
            "environment_url",
            "status",
            "triggered_by",
            "started_at",
            "finished_at",
            "jenkins_build_url",
            "allure_report_url",
            "actions",
        ]

    def get_job_name(self, obj: JenkinsTask) -> str:
        return obj.job_full_name

    def get_triggered_by(self, obj: JenkinsTask) -> str | None:
        return obj.triggered_by.display_name if obj.triggered_by else None

    def _job_path(self, job_full_name: str) -> str:
        return "/".join(f"job/{urllib.parse.quote(part)}" for part in job_full_name.split("/") if part)

    def _public_base_url(self) -> str:
        return os.environ.get("JENKINS_PUBLIC_BASE_URL", os.environ.get("JENKINS_API_BASE_URL", "")).rstrip("/")

    def get_jenkins_build_url(self, obj: JenkinsTask) -> str:
        if obj.jenkins_build_url:
            return f"{obj.jenkins_build_url.rstrip('/')}/"
        if not obj.build_number:
            return ""
        public_base_url = self._public_base_url()
        if not public_base_url:
            return ""
        return f"{public_base_url}/{self._job_path(obj.job_full_name)}/{obj.build_number}/"

    def get_allure_report_url(self, obj: JenkinsTask) -> str:
        if not obj.build_number:
            return ""
        build_url = self.get_jenkins_build_url(obj)
        if not build_url:
            return ""
        # 历史任务可能保存了 artifact HTML 地址，统一按具体 build 规范化到 Allure 插件入口。
        return f"{build_url.rstrip('/')}/allure/"

    def get_actions(self, obj: JenkinsTask) -> dict[str, bool]:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        can_cancel = obj.status in {"queued", "running"} and (
            getattr(user, "role", None) == "admin" or (obj.triggered_by_id and obj.triggered_by_id == getattr(user, "id", None))
        )
        return {
            "cancel": bool(can_cancel),
            "view_report": bool(self.get_allure_report_url(obj)),
            "view_jenkins_task": bool(self.get_jenkins_build_url(obj)),
        }


class JenkinsTaskListResponseSerializer(serializers.Serializer):
    data = JenkinsTaskSerializer(many=True)
    meta = PaginationMetaSerializer()


class JenkinsTaskResponseSerializer(serializers.Serializer):
    data = JenkinsTaskSerializer()


class JenkinsTaskBulkSyncRequestSerializer(serializers.Serializer):
    discover_daily = serializers.BooleanField()
    date = serializers.DateField(required=False)


class JenkinsTaskBulkSyncDataSerializer(serializers.Serializer):
    created_count = serializers.IntegerField(min_value=0)
    updated_count = serializers.IntegerField(min_value=0)
    synced_count = serializers.IntegerField(min_value=0)


class JenkinsTaskBulkSyncResponseSerializer(serializers.Serializer):
    data = JenkinsTaskBulkSyncDataSerializer()


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
