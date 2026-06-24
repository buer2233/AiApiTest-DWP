"""测试任务 API 序列化模块。
本模块定义测试任务创建、任务输出、失败用例输出和重试请求的参数结构。
序列化器只负责 API 数据校验和展示，不直接拼接 pytest 或 Jenkins 命令。
"""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import FailureCase, TestRun


class TestRunCreateSerializer(serializers.Serializer):
    """测试任务创建参数序列化器。
    支持按模块路径执行、按 node id 执行以及设置重试模式和重试次数。
    """

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
    """测试任务输出序列化器。
    输出任务基础字段、执行产物路径、执行摘要、触发用户以及聚合的失败用例数量。
    """

    triggered_by = UserSerializer(read_only=True)
    failure_count = serializers.IntegerField(read_only=True)

    class Meta:
        """绑定 TestRun 模型并把输出字段全部设为只读。"""

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
    """失败用例输出序列化器。
    用于失败用例弹窗展示 node id、用例名、错误类型、断言信息和重试状态。
    """

    class Meta:
        """绑定 FailureCase 模型并限制 API 只读输出。"""

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
    """选择失败用例重试的请求序列化器。"""

    failure_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    retry_count = serializers.IntegerField(min_value=0, default=0)


class RetryCountSerializer(serializers.Serializer):
    """一键失败重试请求序列化器。"""

    retry_count = serializers.IntegerField(min_value=0, default=0)


class RetryModuleSerializer(serializers.Serializer):
    """模块重试请求序列化器。"""

    module_path = serializers.CharField(max_length=500)
    retry_count = serializers.IntegerField(min_value=0, default=0)
