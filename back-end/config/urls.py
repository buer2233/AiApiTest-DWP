"""根 URL 路由。

- /admin/        Django Admin（管理员审批入口）
- /api/auth/     认证模块（注册/登录/登出/当前用户）
- /api/testcases/ 用例模块（同步/列表）
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/testcases/", include("apps.testcases.urls")),
]
