from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.testcases.models import TestCaseItem
from apps.testcases.serializers import TestCaseItemSerializer
from apps.testcases.services.scanner import sync_pytest_cases
from common.pagination import paginate_queryset
from common.permissions import IsAdminRole
from common.response import success_response


class TestCaseSyncView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        return success_response(sync_pytest_cases())


class TestCaseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = TestCaseItem.objects.all()
        sync_status = request.query_params.get("sync_status", TestCaseItem.SyncStatus.SYNCED).strip()
        keyword = request.query_params.get("keyword", "").strip()
        package_name = request.query_params.get("package_name", "").strip()
        module_name = request.query_params.get("module_name", "").strip()

        if sync_status:
            if sync_status not in TestCaseItem.SyncStatus.values:
                raise ValidationError({"sync_status": "同步状态不合法"})
            queryset = queryset.filter(sync_status=sync_status)
        if package_name:
            queryset = queryset.filter(package_name=package_name)
        if module_name:
            queryset = queryset.filter(module_name=module_name)
        if keyword:
            queryset = queryset.filter(
                Q(node_id__icontains=keyword)
                | Q(function_name__icontains=keyword)
                | Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(module_name__icontains=keyword)
            )

        page_items, meta = paginate_queryset(request, queryset)
        return success_response(TestCaseItemSerializer(page_items, many=True).data, meta=meta)
