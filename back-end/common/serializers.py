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
