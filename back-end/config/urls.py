"""Django 全局路由配置模块。
本模块挂载管理后台、OpenAPI 文档、认证 API、测试任务 API、Jenkins API 和受控 Allure 报告入口。
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.test_runs.views import serve_allure_report


urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI schema、Swagger 和 Redoc 用于前后端联调和接口说明。
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="api-redoc",
    ),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/test-runs/", include("apps.test_runs.urls")),
    path("api/jenkins/", include("apps.jenkins_integration.urls")),
    # Allure 报告静态入口由 test_runs 视图做根目录校验后再交给 Django serve。
    path("reports/<str:run_id>/", serve_allure_report, name="allure-report-index"),
    path("reports/<str:run_id>/<path:path>", serve_allure_report, name="allure-report-asset"),
]
