from django.conf import settings
from django.http import HttpResponse


class SimpleCorsMiddleware:
    """提供本地前端联调所需的最小 CORS 能力，生产环境可通过环境变量收敛来源。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin", "")
        allow_origin = "*" if settings.CORS_ALLOW_ALL else origin if origin in settings.CORS_ALLOWED_ORIGINS else ""
        if allow_origin:
            response["Access-Control-Allow-Origin"] = allow_origin
            response["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization,Content-Type"
        return response
