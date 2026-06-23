from django.conf import settings


def test_database_connection_is_forced_to_local_mysql():
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.mysql"
    assert database["HOST"] == "localhost"
    assert database["PORT"] == "3306"
    assert "sqlite" not in str(database["NAME"]).lower()
