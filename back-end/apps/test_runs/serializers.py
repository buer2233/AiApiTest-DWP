from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import FailureCase, TestRun


class TestRunCreateSerializer(serializers.Serializer):
    case_path = serializers.CharField(max_length=500)
    node_ids = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        required=False,
        allow_empty=True,
    )
    retry_mode = serializers.ChoiceField(
        choices=TestRun.RetryMode.choices,
        default=TestRun.RetryMode.NONE,
    )
    retry_count = serializers.IntegerField(min_value=0, default=0)


class TestRunSerializer(serializers.ModelSerializer):
    triggered_by = UserSerializer(read_only=True)
    failure_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TestRun
        fields = [
            "id",
            "run_id",
            "case_path",
            "node_ids",
            "retry_mode",
            "retry_count",
            "status",
            "triggered_by",
            "trigger_source",
            "parent_run",
            "report_path",
            "allure_results_path",
            "console_log_path",
            "started_at",
            "finished_at",
            "summary",
            "failure_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FailureCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailureCase
        fields = [
            "id",
            "test_run",
            "node_id",
            "case_name",
            "module_path",
            "description",
            "error_type",
            "assertion_message",
            "status",
            "retry_status",
            "last_retry_run",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RetrySelectedSerializer(serializers.Serializer):
    failure_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    retry_count = serializers.IntegerField(min_value=0, default=0)


class RetryCountSerializer(serializers.Serializer):
    retry_count = serializers.IntegerField(min_value=0, default=0)


class RetryModuleSerializer(serializers.Serializer):
    module_path = serializers.CharField(max_length=500)
    retry_count = serializers.IntegerField(min_value=0, default=0)
