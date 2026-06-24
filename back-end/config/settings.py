"""Django 后端全局配置模块。
本模块集中配置 DRF、Token 认证、本地 MySQL、CORS、Jenkins 凭据入口和 Allure 报告根目录。
敏感配置必须通过环境变量提供，仓库内只保留开发占位默认值。
"""

import os
from pathlib import Path


# BASE_DIR 指向 back-end 目录，跨模块路径会通过 BASE_DIR.parent 回到仓库根目录。
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# 后端只安装平台需要的 Django/DRF 组件和三个业务应用。
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "corsheaders",
    "apps.accounts",
    "apps.test_runs",
    "apps.jenkins_integration",
]

# CORS 中间件需要尽量靠前，确保浏览器预检请求能正确返回跨域头。
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# 项目约定默认使用本地 MySQL，连接信息通过环境变量覆盖，不回退 SQLite。
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "ai_api_test_platform"),
        "USER": os.getenv("MYSQL_USER", "root"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "HOST": "localhost",
        "PORT": os.getenv("MYSQL_PORT", "3307"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# 第一版平台不启用复杂密码强度校验，便于本地测试和 CI 初始化用户。
AUTH_PASSWORD_VALIDATORS = []
AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF 默认使用 TokenAuthentication；公开接口需要在视图中显式清空权限配置。
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# drf-spectacular 负责生成 OpenAPI、Swagger 和 Redoc 文档。
SPECTACULAR_SETTINGS = {
    "TITLE": "AiApiTest-DWP API",
    "DESCRIPTION": "CICD AI 自动化测试平台后端接口文档",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "AUTHENTICATION_WHITELIST": [
        "rest_framework.authentication.TokenAuthentication",
    ],
}

# 前端 Vite 开发服务默认允许访问后端 API，生产环境应通过环境变量收紧。
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Jenkins 凭据入口只读取环境变量，不在仓库内保存真实 URL、用户名或 API Token。
JENKINS_BASE_URL = os.getenv("JENKINS_BASE_URL", "")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME", "")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN", "")
JENKINS_DEFAULT_JOB = os.getenv("JENKINS_DEFAULT_JOB", "api-test")

# Allure 静态报告只能从该根目录下对外服务，防止 report_path 暴露任意服务器文件。
ALLURE_REPORTS_ROOT = os.getenv(
    "ALLURE_REPORTS_ROOT",
    str(BASE_DIR.parent / "api-test" / "runtime" / "ci-runs"),
)
