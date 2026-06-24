"""Jenkins API 序列化模块。
本模块校验前端触发 Jenkins 构建时传入的测试参数，并转换为 Jenkinsfile 约定的大写参数名。
"""

from rest_framework import serializers


class TriggerBuildSerializer(serializers.Serializer):
    """触发 Jenkins 构建的请求序列化器。
    字段保持前端友好命名，`to_jenkins_parameters()` 负责转换为 Pipeline 参数。
    """

    case_path = serializers.CharField(
        max_length=500,
        default="test_case/test_gbif_case",
    )
    pytest_node_ids = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        required=False,
        allow_empty=True,
    )
    retry_mode = serializers.ChoiceField(
        choices=["none", "selected", "all-failed", "module"],
        default="none",
    )
    retry_count = serializers.IntegerField(min_value=0, default=0)
    clean_allure = serializers.BooleanField(default=True)
    open_report = serializers.BooleanField(default=False)

    def to_jenkins_parameters(self) -> dict:
        """转换为 Jenkins 参数化构建所需字段。
        Returns:
            dict: 与 Stage 4 Jenkinsfile 保持一致的大写参数字典。
        """
        data = self.validated_data
        return {
            "CASE_PATH": data["case_path"],
            # Jenkins 文本参数用换行承载多个 pytest node id，便于人工复制粘贴。
            "PYTEST_NODE_IDS": "\n".join(data.get("pytest_node_ids") or []),
            "RETRY_MODE": data["retry_mode"],
            "RETRY_COUNT": str(data["retry_count"]),
            "CLEAN_ALLURE": _bool_string(data["clean_allure"]),
            "OPEN_REPORT": _bool_string(data["open_report"]),
        }


def _bool_string(value: bool) -> str:
    """把布尔值转换成 Jenkins 参数需要的小写字符串。"""
    return "true" if value else "false"
