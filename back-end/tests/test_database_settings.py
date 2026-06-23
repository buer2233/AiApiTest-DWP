from django.conf import settings


def test_database_connection_uses_docker_mysql_on_localhost():
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.mysql"
    assert database["HOST"] == "localhost"
    assert database["PORT"] == "3307"
    assert "sqlite" not in str(database["NAME"]).lower()
