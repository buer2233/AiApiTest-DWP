"""testcases 视图：用例同步（admin）与用例列表（登录可见）。"""
from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.permissions import IsAdminRole
from common.response import success

from .models import TestCaseSnapshot
from .serializers import TestCaseSnapshotSerializer
from .services.sync import sync_test_cases


class TestCaseSyncView(APIView):
    """F6 用例同步：IsAuthenticated + IsAdminRole。"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        result = sync_test_cases()
        return success(data=result, message="同步完成")


class TestCaseListView(ListAPIView):
    """F7 用例列表：登录可见，分页 + 模块/关键词筛选，仅返回启用用例。"""

    permission_classes = [IsAuthenticated]
    serializer_class = TestCaseSnapshotSerializer

    def get_queryset(self):
        qs = TestCaseSnapshot.objects.filter(is_active=True).order_by("module_key", "node_id")
        module_key = self.request.query_params.get("module_key")
        keyword = self.request.query_params.get("keyword")
        if module_key:
            qs = qs.filter(module_key=module_key)
        if keyword:
            qs = qs.filter(
                Q(node_id__icontains=keyword)
                | Q(case_title__icontains=keyword)
                | Q(function_name__icontains=keyword)
            )
        return qs
