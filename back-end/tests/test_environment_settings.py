import importlib
from pathlib import Path

from config.settings import base


def test_load_env_file_sets_missing_values_without_overwriting_process_env(tmp_path):
    """根 .env 读取只补缺失值，避免覆盖调用方显式注入的环境变量。"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "MYSQL_DATABASE=from-file",
                "MYSQL_ROOT_PASSWORD=file-password",
                "IGNORED_LINE",
                "# comment",
            ]
        ),
        encoding="utf-8",
    )
    target_env = {"MYSQL_DATABASE": "from-process"}

    base.load_env_file(env_file, target_env)

    assert target_env["MYSQL_DATABASE"] == "from-process"
    assert target_env["MYSQL_ROOT_PASSWORD"] == "file-password"
    assert "IGNORED_LINE" not in target_env


def test_build_database_config_derives_host_port_and_uses_application_credentials():
    """数据库仅使用应用账号，主机/宿主机端口从平台基础量派生。"""
    database_config = base.build_database_config(
        {
            "PLATFORM_BIND_HOST": "10.10.0.8",
            "MYSQL_HOST_PORT": "3310",
            "DB_USER": "platform-app",
            "DB_PASSWORD": "app-password",
        },
        Path("back-end"),
    )

    default_db = database_config["default"]
    assert default_db["ENGINE"] == "django.db.backends.mysql"
    assert default_db["NAME"] == "ai_api_test_platform"
    assert default_db["USER"] == "platform-app"
    assert default_db["PASSWORD"] == "app-password"
    assert default_db["HOST"] == "10.10.0.8"
    assert default_db["PORT"] == "3310"
    assert default_db["CONN_MAX_AGE"] == 60
    assert default_db["OPTIONS"]["charset"] == "utf8mb4"


def test_build_database_config_never_uses_mysql_root_password_for_application_connection():
    """MySQL root 密码只供 MySQL 管理，不得传播给后端应用连接。"""
    database_config = base.build_database_config(
        {
            "MYSQL_ROOT_PASSWORD": "root-password",
            "DB_USER": "platform-app",
        },
        Path("back-end"),
    )

    assert database_config["default"]["USER"] == "platform-app"
    assert database_config["default"]["PASSWORD"] == ""


def test_build_database_config_uses_compose_internal_database_endpoint_when_provided():
    """容器服务可显式提供固定的 Compose 内部端点，不依赖根配置。"""
    database_config = base.build_database_config(
        {
            "DB_HOST": "mysql",
            "DB_PORT": "3306",
            "DB_USER": "platform-app",
            "DB_PASSWORD": "app-password",
        },
        Path("back-end"),
    )

    assert database_config["default"]["ENGINE"] == "django.db.backends.mysql"
    assert database_config["default"]["HOST"] == "mysql"
    assert database_config["default"]["PORT"] == "3306"


def test_fixed_django_and_cookie_settings_ignore_legacy_environment_overrides(monkeypatch):
    """固定策略由 settings 代码持有，旧环境覆盖项不会改变行为。"""
    monkeypatch.setenv("DJANGO_DEBUG", "true")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "attacker.invalid")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("AUTH_COOKIE_NAME", "legacy-cookie")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")

    assert base.DEBUG is False
    assert "attacker.invalid" not in base.ALLOWED_HOSTS
    assert base.TIME_ZONE == "Asia/Shanghai"
    assert base.AUTH_COOKIE_NAME == "authToken"
    assert base.AUTH_COOKIE_SECURE is False


def test_platform_public_endpoints_are_derived_from_host_scheme_and_ports(monkeypatch):
    """公开服务地址和 API 入口由平台主机、协议和端口统一派生。"""
    with monkeypatch.context() as scoped_env:
        scoped_env.setenv("PLATFORM_BIND_HOST", "0.0.0.0")
        scoped_env.setenv("PLATFORM_PUBLIC_HOST", "platform.example.test")
        scoped_env.setenv("PLATFORM_PUBLIC_SCHEME", "https")
        scoped_env.setenv("JENKINS_HTTP_PORT", "18080")
        scoped_env.setenv("BACKEND_HOST_PORT", "18000")
        scoped_env.setenv("FRONTEND_HOST_PORT", "15173")

        importlib.reload(base)
        assert base.build_public_url("platform.example.test", 18000) == "https://platform.example.test:18000"
        assert base.JENKINS_PUBLIC_BASE_URL == "https://platform.example.test:18080"
        assert base.BACKEND_API_BASE_URL == "https://platform.example.test:18000/api/v1"
        assert base.AUTH_COOKIE_SECURE is True
    importlib.reload(base)


def test_public_url_brackets_bare_or_bracketed_ipv6_host():
    """IPv6 公开主机在 URL 中必须且只能出现一层方括号。"""
    assert base.build_public_url("2001:db8::1", 8000, "https") == "https://[2001:db8::1]:8000"
    assert base.build_public_url("[2001:db8::1]", 8000, "https") == "https://[2001:db8::1]:8000"


def test_environment_catalog_service_token_is_read_directly_from_backend_environment():
    """backend 无需 Jenkins SCM 配置即可读取专用服务令牌。"""
    env = {
        "ENVIRONMENT_CATALOG_SERVICE_TOKEN": "private-token",
    }
    assert base.resolve_environment_catalog_service_token(env) == "private-token"


def test_fixed_jenkins_defaults_ignore_retired_environment_overrides(monkeypatch):
    """固定 Job 名及请求、轮询常量不能再被根环境变量覆盖。"""
    monkeypatch.setenv("JENKINS_FAILED_RERUN_JOB_NAME", "legacy-failed")
    monkeypatch.setenv("JENKINS_MODULE_RERUN_JOB_NAME", "legacy-module")
    monkeypatch.setenv("JENKINS_DAILY_FULL_JOB_NAME", "legacy-daily")
    monkeypatch.setenv("JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME", "legacy-catalog")
    monkeypatch.setenv("JENKINS_REQUEST_TIMEOUT_SECONDS", "999")
    monkeypatch.setenv("JENKINS_BUILD_POLL_INTERVAL_SECONDS", "999")

    assert base.JENKINS_FAILED_RERUN_JOB_NAME == "AiApiTest-DWP-Failed-Rerun"
    assert base.JENKINS_MODULE_RERUN_JOB_NAME == "AiApiTest-DWP-Module-Rerun"
    assert base.JENKINS_DAILY_FULL_JOB_NAME == "AiApiTest-DWP-Daily-Full-Module"
    assert base.JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME == "AiApiTest-DWP-Environment-Catalog-Sync"
    assert base.JENKINS_REQUEST_TIMEOUT_SECONDS == 15
    assert base.JENKINS_BUILD_POLL_INTERVAL_SECONDS == 10
