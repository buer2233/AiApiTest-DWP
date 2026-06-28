from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.views import exception_handler

from common.response import error_response


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "资源状态冲突"
    default_code = "conflict"

    def __init__(self, code: str, message: str, details=None):
        super().__init__(detail=message, code=code)
        self.business_code = code
        self.details = details


class BadRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "请求参数不合法"
    default_code = "bad_request"

    def __init__(self, code: str, message: str, details=None):
        super().__init__(detail=message, code=code)
        self.business_code = code
        self.details = details


class InternalServerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "服务端处理失败"
    default_code = "internal_error"

    def __init__(self, code: str, message: str, details=None):
        super().__init__(detail=message, code=code)
        self.business_code = code
        self.details = details


def _validation_details(exc: ValidationError):
    if isinstance(exc.detail, dict):
        return [{"field": field, "message": value} for field, value in exc.detail.items()]
    return exc.detail


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        return error_response(
            "validation_error",
            "请求参数不合法",
            status_code=response.status_code,
            details=_validation_details(exc),
        )
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return error_response("unauthorized", "请先登录", status_code=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, PermissionDenied):
        return error_response("forbidden", "无权执行该操作", status_code=status.HTTP_403_FORBIDDEN)

    code = getattr(exc, "business_code", None) or getattr(exc, "default_code", "api_error")
    details = getattr(exc, "details", None)
    message = str(exc.detail) if hasattr(exc, "detail") else "接口请求失败"
    return error_response(code, message, status_code=response.status_code, details=details)
