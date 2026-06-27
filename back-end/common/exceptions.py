"""自定义业务异常与 DRF 统一异常处理。

所有错误最终输出 {code, message, errors} + 对应 HTTP 状态码，
与需求 §7 的统一响应契约一致。
"""
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .response import BizCode


class BizError(Exception):
    """业务异常：携带业务码、消息、HTTP 状态与字段级错误。"""

    def __init__(
        self,
        code,
        message,
        http_status_code=http_status.HTTP_400_BAD_REQUEST,
        errors=None,
    ):
        self.code = code
        self.message = message
        self.http_status_code = http_status_code
        self.errors = errors or {}
        super().__init__(message)


def custom_exception_handler(exc, context):
    """把异常统一成 {code, message, errors} + 对应 HTTP 状态码。"""
    # 1) 业务异常优先
    if isinstance(exc, BizError):
        return Response(
            {"code": exc.code, "message": exc.message, "errors": exc.errors},
            status=exc.http_status_code,
        )

    # 2) 交给 DRF 默认处理（认证 401、权限 403、参数校验 400 等）
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    detail = response.data

    if status_code == http_status.HTTP_401_UNAUTHORIZED:
        code = BizCode.UNAUTHENTICATED
        message = "未认证或登录已失效"
    elif status_code == http_status.HTTP_403_FORBIDDEN:
        code = BizCode.NO_PERMISSION
        message = "无权限执行该操作"
    else:
        code = BizCode.VALIDATION_ERROR
        message = "请求参数校验失败"

    errors = detail if isinstance(detail, dict) else {"detail": detail}
    return Response(
        {"code": code, "message": message, "errors": errors},
        status=status_code,
    )
