"""用例模块路由：同步 / 列表。"""
from django.urls import path

from .views import TestCaseListView, TestCaseSyncView

app_name = "testcases"

urlpatterns = [
    path("sync/", TestCaseSyncView.as_view(), name="sync"),
    path("", TestCaseListView.as_view(), name="list"),
]
