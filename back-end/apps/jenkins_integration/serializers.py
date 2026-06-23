from rest_framework import serializers


class TriggerBuildSerializer(serializers.Serializer):
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
        data = self.validated_data
        return {
            "CASE_PATH": data["case_path"],
            "PYTEST_NODE_IDS": "\n".join(data.get("pytest_node_ids") or []),
            "RETRY_MODE": data["retry_mode"],
            "RETRY_COUNT": str(data["retry_count"]),
            "CLEAN_ALLURE": _bool_string(data["clean_allure"]),
            "OPEN_REPORT": _bool_string(data["open_report"]),
        }


def _bool_string(value: bool) -> str:
    return "true" if value else "false"
