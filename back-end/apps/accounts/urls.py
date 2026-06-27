"""认证模块路由：注册 / 登录 / 登出 / 当前用户。"""
from django.urls import path

from .views import LoginView, LogoutView, MeView, RegisterView

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
