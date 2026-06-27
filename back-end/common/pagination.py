"""标准分页：默认每页 20，上限 100，响应包裹统一格式。"""
from rest_framework.pagination import PageNumberPagination

from .response import success


class StandardPagination(PageNumberPagination):
    """分页器：page/page_size 查询参数，超过 max_page_size 自动截断。"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        # 包进统一成功响应：data = {count, next, previous, results}
        return success(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
