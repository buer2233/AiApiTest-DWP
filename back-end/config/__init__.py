try:
    import pymysql
except ImportError:  # pragma: no cover - 本地 sqlite 测试不需要 MySQL 驱动。
    pymysql = None

if pymysql is not None:  # pragma: no cover - 容器化 MySQL 部署时启用。
    pymysql.install_as_MySQLdb()
