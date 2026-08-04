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


def _parse_port(value: str | None, fallback: int) -> int:
    """解析公开端口；非法值回退到代码级默认，避免启动时产生隐式异常。"""
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return fallback
    return parsed if 1 <= parsed <= 65535 else fallback


def build_public_url(host: str, port: int, scheme: str | None = None) -> str:
    """根据平台公开主机、协议和端口生成服务入口。"""
    selected_scheme = scheme or PLATFORM_PUBLIC_SCHEME
    normalized_host = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    url_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    return f"{selected_scheme}://{url_host}:{port}"


def _host_variants(host: str) -> set[str]:
    """生成 Django Host 校验所需的裸主机和 IPv6 方括号形式。"""
    normalized = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    return {normalized, f"[{normalized}]"} if ":" in normalized else {normalized}


def resolve_environment_catalog_service_token(env: MutableMapping[str, str]) -> str:
    """读取 backend 专用服务令牌；启用同步时的条件校验由部署预检负责。"""
    return env.get("ENVIRONMENT_CATALOG_SERVICE_TOKEN", "")


def build_database_config(env: MutableMapping[str, str], base_dir: Path) -> dict[str, dict[str, object]]:
    """构造 MySQL 配置；应用账号和数据库连接参数与 root 管理凭据隔离。"""
    database_user = env.get("DB_USER", "aiapitest_platform")
    database_password = env.get("DB_PASSWORD", "")
    # Compose 容器显式提供 mysql:3306；本地运行时回退到平台绑定地址和宿主机映射端口。
    database_host = env.get("DB_HOST") or env.get("PLATFORM_BIND_HOST", PLATFORM_BIND_HOST)
    database_port = env.get("DB_PORT") or str(_parse_port(env.get("MYSQL_HOST_PORT"), MYSQL_HOST_PORT))
    return {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "ai_api_test_platform",
            "USER": database_user,
            "PASSWORD": database_password,
            "HOST": database_host,
            "PORT": database_port,
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }


load_env_file(REPO_ROOT / ".env")

# 仅把密钥和部署差异交给环境变量；固定协议常量由本模块统一维护。
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = False

PLATFORM_BIND_HOST = os.getenv("PLATFORM_BIND_HOST", "127.0.0.1")
PLATFORM_PUBLIC_HOST = os.getenv("PLATFORM_PUBLIC_HOST", "127.0.0.1")
PLATFORM_PUBLIC_SCHEME = os.getenv("PLATFORM_PUBLIC_SCHEME", "http").lower()
if PLATFORM_PUBLIC_SCHEME not in {"http", "https"}:
    PLATFORM_PUBLIC_SCHEME = "http"

MYSQL_HOST_PORT = _parse_port(os.getenv("MYSQL_HOST_PORT"), 3307)
JENKINS_HTTP_PORT = _parse_port(os.getenv("JENKINS_HTTP_PORT"), 8080)
JENKINS_AGENT_PORT = _parse_port(os.getenv("JENKINS_AGENT_PORT"), 50001)
BACKEND_HOST_PORT = _parse_port(os.getenv("BACKEND_HOST_PORT"), 8000)
FRONTEND_HOST_PORT = _parse_port(os.getenv("FRONTEND_HOST_PORT"), 5173)

API_BASE_PATH = "/api/v1"
BACKEND_SERVICE_URL = build_public_url(PLATFORM_PUBLIC_HOST, BACKEND_HOST_PORT)
BACKEND_API_BASE_URL = f"{BACKEND_SERVICE_URL}{API_BASE_PATH}"
FRONTEND_SERVICE_URL = build_public_url(PLATFORM_PUBLIC_HOST, FRONTEND_HOST_PORT)
JENKINS_PUBLIC_BASE_URL = build_public_url(PLATFORM_PUBLIC_HOST, JENKINS_HTTP_PORT)
JENKINS_API_BASE_URL = "http://jenkins:8080"
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME", "")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN", "")
JENKINS_REQUEST_TIMEOUT_SECONDS = 15
JENKINS_BUILD_POLL_INTERVAL_SECONDS = 10
JENKINS_FAILED_RERUN_JOB_NAME = "AiApiTest-DWP-Failed-Rerun"
JENKINS_MODULE_RERUN_JOB_NAME = "AiApiTest-DWP-Module-Rerun"
JENKINS_DAILY_FULL_JOB_NAME = "AiApiTest-DWP-Daily-Full-Module"
JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME = "AiApiTest-DWP-Environment-Catalog-Sync"
ALLOWED_HOSTS = sorted(
    {
        "localhost",
        "127.0.0.1",
        "backend",
        "frontend",
        *_host_variants(PLATFORM_BIND_HOST),
        *_host_variants(PLATFORM_PUBLIC_HOST),
    }
)

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
TIME_ZONE = "Asia/Shanghai"

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

AUTH_COOKIE_NAME = "authToken"
AUTH_COOKIE_MAX_AGE_SECONDS = 28800
AUTH_COOKIE_SECURE = PLATFORM_PUBLIC_SCHEME == "https"
AUTH_COOKIE_SAMESITE = "Lax"
AUTH_COOKIE_PATH = "/"
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", SECRET_KEY)
AUTH_TOKEN_ISSUER = "AiApiTest-DWP"
# 仅 Jenkins 专用 Credentials 对应的私有令牌可调用环境目录内部接口；不提供开发默认值。
ENVIRONMENT_CATALOG_SERVICE_TOKEN = resolve_environment_catalog_service_token(os.environ)

DATABASES = build_database_config(os.environ, BASE_DIR)
