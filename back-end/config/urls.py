from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.views import (
    AuthMeView,
    InvitationListCreateView,
    InvitationRevokeView,
    LoginView,
    LogoutView,
    RegisterView,
    UserListView,
)
from metrics.views import EnvironmentSummaryView, ModuleSnapshotListView, TestEnvironmentListView


urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/me", AuthMeView.as_view(), name="auth-me"),
    path("api/v1/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/v1/users", UserListView.as_view(), name="user-list"),
    path("api/v1/invitations", InvitationListCreateView.as_view(), name="invitation-list-create"),
    path(
        "api/v1/invitations/<int:invitation_id>/revoke",
        InvitationRevokeView.as_view(),
        name="invitation-revoke",
    ),
    path("api/v1/test-environments", TestEnvironmentListView.as_view(), name="test-environment-list"),
    path(
        "api/v1/test-environments/<int:environment_id>/summary",
        EnvironmentSummaryView.as_view(),
        name="test-environment-summary",
    ),
    path("api/v1/module-snapshots", ModuleSnapshotListView.as_view(), name="module-snapshot-list"),
]
