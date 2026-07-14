from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.health import evaluate_readiness
from common.serializers import (
    LiveHealthResponseSerializer,
    ReadyHealthResponseSerializer,
    UnreadyHealthResponseSerializer,
)


class LiveHealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        auth=[],
        responses={
            200: OpenApiResponse(
                LiveHealthResponseSerializer,
                description="DRF 进程存活",
            )
        },
    )
    def get(self, request):
        return Response(
            {
                "code": "ok",
                "message": "service is alive",
                "data": {"status": "live"},
            }
        )


class ReadyHealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        auth=[],
        responses={
            200: OpenApiResponse(
                ReadyHealthResponseSerializer,
                description="必要配置、数据库和 schema 均已就绪",
            ),
            503: OpenApiResponse(
                UnreadyHealthResponseSerializer,
                description="配置、数据库或 schema 尚未就绪",
            ),
        },
    )
    def get(self, request):
        readiness = evaluate_readiness()
        if readiness.ready:
            return Response(
                {
                    "code": "ok",
                    "message": "service is ready",
                    "data": {
                        "status": "ready",
                        "checks": readiness.checks,
                    },
                }
            )

        return Response(
            {
                "code": "service_not_ready",
                "message": "service is not ready",
                "data": {
                    "status": "not_ready",
                    "failed_check": readiness.failed_check,
                    "reason_code": readiness.reason_code,
                    "checks": readiness.checks,
                },
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
