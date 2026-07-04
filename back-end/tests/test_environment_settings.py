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


def test_build_database_config_defaults_to_mysql_and_reuses_compose_variables():
    """正式运行默认使用 Docker MySQL，并和 Compose 的 MYSQL_* 变量保持一致。"""
    database_config = base.build_database_config(
        {
            "MYSQL_DATABASE": "ai_api_test_platform",
            "MYSQL_ROOT_PASSWORD": "root-password",
            "MYSQL_BIND_HOST": "127.0.0.1",
            "MYSQL_HOST_PORT": "3307",
        },
        Path("back-end"),
    )

    default_db = database_config["default"]
    assert default_db["ENGINE"] == "django.db.backends.mysql"
    assert default_db["NAME"] == "ai_api_test_platform"
    assert default_db["USER"] == "root"
    assert default_db["PASSWORD"] == "root-password"
    assert default_db["HOST"] == "127.0.0.1"
    assert default_db["PORT"] == "3307"
    assert default_db["OPTIONS"]["charset"] == "utf8mb4"


def test_build_database_config_uses_root_password_for_default_root_user():
    """默认 root 连接必须优先使用 Compose 初始化 root 时的 MYSQL_ROOT_PASSWORD。"""
    database_config = base.build_database_config(
        {
            "MYSQL_DATABASE": "ai_api_test_platform",
            "MYSQL_ROOT_PASSWORD": "root-password",
            "MYSQL_PASSWORD": "non-root-password",
        },
        Path("back-end"),
    )

    assert database_config["default"]["USER"] == "root"
    assert database_config["default"]["PASSWORD"] == "root-password"


def test_build_database_config_keeps_sqlite_when_explicitly_requested():
    """测试环境或回退场景显式指定 sqlite 时，仍可使用 SQLite。"""
    database_config = base.build_database_config(
        {
            "DB_ENGINE": "sqlite",
            "SQLITE_DB_PATH": "custom.sqlite3",
        },
        Path("back-end"),
    )

    assert database_config["default"] == {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "custom.sqlite3",
    }
