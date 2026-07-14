from rest_framework import serializers


class PaginationMetaSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    per_page = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class ApiErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.ListField(child=serializers.JSONField())


class ApiErrorResponseSerializer(serializers.Serializer):
    error = ApiErrorDetailSerializer()


class LiveHealthDataSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["live"])


class LiveHealthResponseSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=["ok"])
    message = serializers.CharField()
    data = LiveHealthDataSerializer()


class HealthChecksSerializer(serializers.Serializer):
    configuration = serializers.ChoiceField(choices=["valid", "invalid", "unknown"])
    database = serializers.ChoiceField(choices=["available", "unavailable", "unknown"])
    schema = serializers.ChoiceField(choices=["ready", "not_ready", "unknown"])


class ReadyHealthDataSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ready"])
    checks = HealthChecksSerializer()


class ReadyHealthResponseSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=["ok"])
    message = serializers.CharField()
    data = ReadyHealthDataSerializer()


class UnreadyHealthDataSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["not_ready"])
    failed_check = serializers.ChoiceField(choices=["configuration", "database", "schema"])
    reason_code = serializers.ChoiceField(
        choices=["configuration_invalid", "database_unavailable", "schema_not_ready"]
    )
    checks = HealthChecksSerializer()


class UnreadyHealthResponseSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=["service_not_ready"])
    message = serializers.CharField()
    data = UnreadyHealthDataSerializer()
