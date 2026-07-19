from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.views import LiveHealthView, ReadyHealthView
from accounts.views import (
    AuthMeView,
    InvitationListCreateView,
    InvitationRevokeView,
    LoginView,
    LogoutView,
    RegisterView,
    UserListView,
)
from metrics.views import (
    CaseResultStatusUpdateView,
    EnvironmentSummaryView,
    EnvironmentCatalogSyncAttemptDetailView,
    EnvironmentCatalogSyncAttemptRetryView,
    EnvironmentCatalogSyncCallbackView,
    EnvironmentCatalogSyncExportView,
    TestEnvironmentDetailView,
    TestEnvironmentSyncFromYamlView,
    FailedCaseRetryCreateView,
    JenkinsTaskBulkSyncView,
    JenkinsTaskCancelView,
    JenkinsTaskListView,
    JenkinsTaskSyncView,
    ModuleSnapshotFilterOptionsView,
    ModuleRerunCreateView,
    ModuleSnapshotCasesView,
    ModuleSnapshotJenkinsTasksView,
    ModuleSnapshotListView,
    ModuleSnapshotTrendView,
    TestEnvironmentListView,
)


urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/health/live/", LiveHealthView.as_view(), name="health-live"),
    path("api/v1/health/ready/", ReadyHealthView.as_view(), name="health-ready"),
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
        "api/v1/test-environments/sync-from-yaml",
        TestEnvironmentSyncFromYamlView.as_view(),
        name="test-environment-sync-from-yaml",
    ),
    path(
        "api/v1/test-environments/<int:environment_id>",
        TestEnvironmentDetailView.as_view(),
        name="test-environment-detail",
    ),
    path(
        "api/v1/test-environments/<int:environment_id>/summary",
        EnvironmentSummaryView.as_view(),
        name="test-environment-summary",
    ),
    path(
        "api/v1/environment-catalog-sync-attempts/<int:attempt_id>",
        EnvironmentCatalogSyncAttemptDetailView.as_view(),
        name="environment-catalog-sync-attempt-detail",
    ),
    path(
        "api/v1/environment-catalog-sync-attempts/<int:attempt_id>/retry",
        EnvironmentCatalogSyncAttemptRetryView.as_view(),
        name="environment-catalog-sync-attempt-retry",
    ),
    path(
        "api/v1/internal/environment-catalog-sync-attempts/<str:sync_request_id>/export/",
        EnvironmentCatalogSyncExportView.as_view(),
        name="internal-environment-catalog-sync-export",
    ),
    path(
        "api/v1/internal/environment-catalog-sync-attempts/<str:sync_request_id>/callback/",
        EnvironmentCatalogSyncCallbackView.as_view(),
        name="internal-environment-catalog-sync-callback",
    ),
    path("api/v1/module-snapshots", ModuleSnapshotListView.as_view(), name="module-snapshot-list"),
    path(
        "api/v1/module-snapshots/filter-options",
        ModuleSnapshotFilterOptionsView.as_view(),
        name="module-snapshot-filter-options",
    ),
    path(
        "api/v1/module-snapshots/<int:snapshot_id>/cases",
        ModuleSnapshotCasesView.as_view(),
        name="module-snapshot-cases",
    ),
    path(
        "api/v1/module-snapshots/<int:snapshot_id>/failed-case-retries",
        FailedCaseRetryCreateView.as_view(),
        name="module-snapshot-failed-case-retries",
    ),
    path(
        "api/v1/module-snapshots/<int:snapshot_id>/module-reruns",
        ModuleRerunCreateView.as_view(),
        name="module-snapshot-module-reruns",
    ),
    path(
        "api/v1/module-snapshots/<int:snapshot_id>/jenkins-tasks",
        ModuleSnapshotJenkinsTasksView.as_view(),
        name="module-snapshot-jenkins-tasks",
    ),
    path(
        "api/v1/case-results/<int:case_result_id>/status",
        CaseResultStatusUpdateView.as_view(),
        name="case-result-status",
    ),
    path("api/v1/jenkins-tasks", JenkinsTaskListView.as_view(), name="jenkins-task-list"),
    path("api/v1/jenkins-tasks/sync", JenkinsTaskBulkSyncView.as_view(), name="jenkins-task-bulk-sync"),
    path(
        "api/v1/jenkins-tasks/<int:task_id>/cancel",
        JenkinsTaskCancelView.as_view(),
        name="jenkins-task-cancel",
    ),
    path(
        "api/v1/jenkins-tasks/<int:task_id>/sync",
        JenkinsTaskSyncView.as_view(),
        name="jenkins-task-sync",
    ),
    path(
        "api/v1/module-snapshots/<int:snapshot_id>/trend",
        ModuleSnapshotTrendView.as_view(),
        name="module-snapshot-trend",
    ),
]
