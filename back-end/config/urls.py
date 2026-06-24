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
    path("reports/<str:run_id>/", serve_allure_report, name="allure-report-index"),
    path("reports/<str:run_id>/<path:path>", serve_allure_report, name="allure-report-asset"),
]
