from django.contrib import admin
from django.urls import path

from apps.accounts.views import (
    InviteCodeDisableView,
    InviteCodeListCreateView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)
from apps.testcases.views import TestCaseListView, TestCaseSyncView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/v1/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/me", MeView.as_view(), name="auth-me"),
    path("api/v1/invite-codes", InviteCodeListCreateView.as_view(), name="invite-code-list-create"),
    path("api/v1/invite-codes/<int:pk>/disable", InviteCodeDisableView.as_view(), name="invite-code-disable"),
    path("api/v1/test-cases", TestCaseListView.as_view(), name="test-case-list"),
    path("api/v1/test-cases/sync", TestCaseSyncView.as_view(), name="test-case-sync"),
]
