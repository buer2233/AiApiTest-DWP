"""
基础配置：所有敏感项与环境相关项一律走环境变量，保证容器化可迁移。

- 生产 / Compose：MySQL（host 用 Compose 服务名，凭据走 .env）。
- 测试：由 config/settings/test.py 覆盖为 SQLite 内存库，不依赖外部服务。
"""
import os
from pathlib import Path

# back-end/ 目录（manage.py 所在层）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# 仓库根目录（back-end 的上一级），用于推导 api-test 默认路径
REPO_ROOT = BASE_DIR.parent


def env_bool(name: str, default: str = "False") -> bool:
    """读取布尔型环境变量。"""
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


# --- 安全 ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-change-me")
DEBUG = env_bool("DJANGO_DEBUG", "False")
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]

# --- 应用 ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 第三方
    "rest_framework",
    "rest_framework.authtoken",
    # 业务 app
    "apps.accounts",
    "apps.testcases",
]

MIDDLEWARE = [
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
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- 自定义用户模型（必须在首次 migrate 前确定）---
AUTH_USER_MODEL = "accounts.User"

# --- 数据库（默认 MySQL，全部走环境变量；测试环境覆盖为 SQLite）---
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.mysql"),
        "NAME": os.environ.get("DB_NAME", "hermes_platform"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# --- 密码校验（注册弱密码拦截依赖此处）---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- 国际化与时区 ---
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

# --- 静态文件 ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    # 关闭可浏览 API 的表单渲染依赖，仅保留 JSON（容器化无界面依赖）
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --- api-test 用例根目录（容器内为挂载卷路径，由环境变量注入）---
# 默认指向仓库内 api-test 目录，便于本机开发；容器/CI 通过 API_TEST_ROOT 覆盖。
API_TEST_ROOT = os.environ.get("API_TEST_ROOT", str(REPO_ROOT / "api-test"))
