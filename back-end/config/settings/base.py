from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parent


def load_env_file(env_file: Path, target_env: MutableMapping[str, str] | None = None) -> None:
    """读取根目录 .env，只补充当前进程未显式设置的变量。"""
    actual_env = target_env if target_env is not None else os.environ
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in actual_env:
            actual_env[key] = value.strip().strip('"').strip("'")


def build_database_config(env: MutableMapping[str, str], base_dir: Path) -> dict[str, dict[str, object]]:
    """根据环境变量构造数据库配置，正式运行默认使用 Docker MySQL。"""
    database_engine = env.get("DB_ENGINE", "mysql").lower()
    if database_engine == "sqlite":
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": env.get("SQLITE_DB_PATH", str(base_dir / "db.sqlite3")),
            }
        }
    database_user = env.get("DB_USER") or env.get("MYSQL_USER", "root")
    if env.get("DB_PASSWORD"):
        database_password = env["DB_PASSWORD"]
    elif database_user == "root":
        database_password = env.get("MYSQL_ROOT_PASSWORD") or env.get("MYSQL_PASSWORD", "")
    else:
        database_password = env.get("MYSQL_PASSWORD") or env.get("MYSQL_ROOT_PASSWORD", "")
    return {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env.get("DB_NAME") or env.get("MYSQL_DATABASE", "ai_api_test_platform"),
            "USER": database_user,
            "PASSWORD": database_password,
            "HOST": env.get("DB_HOST") or env.get("MYSQL_HOST") or env.get("MYSQL_BIND_HOST", "127.0.0.1"),
            "PORT": env.get("DB_PORT") or env.get("MYSQL_PORT") or env.get("MYSQL_HOST_PORT", "3306"),
            "CONN_MAX_AGE": int(env.get("DB_CONN_MAX_AGE", "60")),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }


load_env_file(REPO_ROOT / ".env")

# 本地默认值仅用于开发和测试，容器化/正式环境必须通过环境变量覆盖。
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "common",
    "accounts",
    "metrics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = False
USE_TZ = True
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", os.getenv("TZ", "Asia/Shanghai"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AiApiTest-DWP 后端接口文档",
    "DESCRIPTION": "企业级自动化测试平台 DRF API。当前阶段覆盖用户权限底座与 P2 只读通过率接口。",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "UserRoleEnum": "accounts.models.UserAccount.Role",
        "InvitationStatusEnum": "accounts.models.InvitationCode.Status",
        "RunTypeEnum": "metrics.models.TestRun.RunType",
        "RunStatusEnum": "metrics.models.TestRun.Status",
    },
}

AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "authToken")
AUTH_COOKIE_MAX_AGE_SECONDS = int(os.getenv("AUTH_COOKIE_MAX_AGE_SECONDS", "28800"))
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
AUTH_COOKIE_PATH = os.getenv("AUTH_COOKIE_PATH", "/")
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", SECRET_KEY)
AUTH_TOKEN_ISSUER = os.getenv("AUTH_TOKEN_ISSUER", "AiApiTest-DWP")

DATABASES = build_database_config(os.environ, BASE_DIR)
