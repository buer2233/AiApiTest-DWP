"""数据库配置测试。
本文件验证后端默认数据库配置指向本地 MySQL，不允许测试环境回退到 SQLite。
"""

from django.conf import settings


def test_database_connection_uses_docker_mysql_on_localhost():
    """验证当前 settings 使用本地 Docker MySQL 配置。"""
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.mysql"
    assert database["HOST"] == "localhost"
    assert database["PORT"] == "3307"
    assert "sqlite" not in str(database["NAME"]).lower()
