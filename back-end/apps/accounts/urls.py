"""账户 API 路由模块。
本模块声明登录、登出和当前用户信息接口，统一挂载到全局 `/api/auth/` 路径下。
"""

from django.urls import path

from .views import LoginView, LogoutView, MeView


urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]
