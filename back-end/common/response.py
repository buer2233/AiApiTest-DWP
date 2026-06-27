"""统一响应与业务码定义（契约见需求说明书 §7）。"""
from rest_framework.response import Response


class BizCode:
    """业务状态码。0 表示成功，非 0 为各类业务错误。"""

    OK = 0
    # 注册 1001-1004
    USERNAME_TAKEN = 1001
    EMAIL_TAKEN = 1002
    PASSWORD_MISMATCH = 1003
    VALIDATION_ERROR = 1004
    # 登录 1101-1103
    INVALID_CREDENTIALS = 1101
    ACCOUNT_PENDING = 1102
    ACCOUNT_DISABLED = 1103
    # 用例同步 1201-1202
    NO_PERMISSION = 1201
    CASE_ROOT_INVALID = 1202
    # 通用鉴权（未登录）
    UNAUTHENTICATED = 401


def success(data=None, message="ok", http_status=200):
    """统一成功响应：{code:0, message, data}。"""
    return Response(
        {"code": BizCode.OK, "message": message, "data": data},
        status=http_status,
    )
