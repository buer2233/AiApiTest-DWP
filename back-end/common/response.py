from rest_framework.response import Response


def success_response(data=None, *, status_code=200, meta=None, headers=None):
    payload = {"data": data}
    if meta is not None:
        payload["meta"] = meta
    return Response(payload, status=status_code, headers=headers)


def error_response(code: str, message: str, *, status_code=400, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"error": error}, status=status_code)
