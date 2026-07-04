from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApiError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "api_error"

    def __init__(self, *, code: str, message: str, status_code: int, details: list | None = None):
        self.status_code = status_code
        super().__init__({"code": code, "message": message, "details": details or []})


def api_error_response(code: str, message: str, status_code: int, details: list | None = None) -> Response:
    return Response(
        {"error": {"code": code, "message": message, "details": details or []}},
        status=status_code,
    )


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict) and "code" in detail:
        response.data = {
            "error": {
                "code": str(detail.get("code")),
                "message": str(detail.get("message", "")),
                "details": detail.get("details", []),
            }
        }
    else:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "api_error"),
                "message": str(detail),
                "details": [],
            }
        }
    return response
