from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from common.exceptions import api_error_response


def parse_pagination(request) -> tuple[int, int] | Response:
    try:
        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 20))
    except ValueError:
        return api_error_response("validation_error", "分页参数必须为整数。", status.HTTP_422_UNPROCESSABLE_ENTITY)
    if page < 1 or per_page < 1 or per_page > 100:
        return api_error_response("validation_error", "分页参数超出允许范围。", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return page, per_page


def paginated_response(queryset, serializer_class, page: int, per_page: int) -> Response:
    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page
    serializer = serializer_class(queryset[start:end], many=True)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return Response(
        {
            "data": serializer.data,
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            },
        }
    )
