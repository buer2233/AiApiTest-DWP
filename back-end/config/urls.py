from django.urls import path

from accounts.views import (
    AuthMeView,
    InvitationListCreateView,
    InvitationRevokeView,
    LoginView,
    LogoutView,
    RegisterView,
    UserListView,
)


urlpatterns = [
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
]
