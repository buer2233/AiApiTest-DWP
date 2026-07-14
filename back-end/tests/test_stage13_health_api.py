from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings
from django.db import OperationalError, connection
from django.test import override_settings


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_live_health_is_public_and_does_not_access_database(api_client, django_assert_num_queries):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-test-token")

    with django_assert_num_queries(0):
        response = api_client.get("/api/v1/health/live/")

    assert response.status_code == 200
    assert response.data == {
        "code": "ok",
        "message": "service is alive",
        "data": {"status": "live"},
    }


def test_ready_health_returns_frozen_success_contract_without_running_migrations(api_client):
    with patch(
        "django.db.migrations.executor.MigrationExecutor.migration_plan",
        return_value=[],
    ), patch(
        "django.db.migrations.executor.MigrationExecutor.migrate",
        side_effect=AssertionError("readiness must not execute migrations"),
    ):
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 200
    assert response.data == {
        "code": "ok",
        "message": "service is ready",
        "data": {
            "status": "ready",
            "checks": {
                "configuration": "valid",
                "database": "available",
                "schema": "ready",
            },
        },
    }


@override_settings(SECRET_KEY="")
def test_ready_health_reports_configuration_invalid_and_skips_later_checks(api_client):
    with patch.object(
        connection,
        "ensure_connection",
        side_effect=AssertionError("database check must be skipped"),
    ), patch(
        "django.db.migrations.executor.MigrationExecutor.migration_plan",
        side_effect=AssertionError("schema check must be skipped"),
    ):
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 503
    assert response.data == {
        "code": "service_not_ready",
        "message": "service is not ready",
        "data": {
            "status": "not_ready",
            "failed_check": "configuration",
            "reason_code": "configuration_invalid",
            "checks": {
                "configuration": "invalid",
                "database": "unknown",
                "schema": "unknown",
            },
        },
    }


@pytest.mark.parametrize(
    "databases",
    [
        {},
        {"default": None},
        {"default": []},
        {"default": {"NAME": "platform"}},
        {"default": {"ENGINE": "django.db.backends.sqlite3"}},
        {"default": {"ENGINE": None, "NAME": "platform"}},
        {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": None}},
        {"default": {"ENGINE": "   ", "NAME": "platform"}},
        {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "   "}},
    ],
    ids=[
        "default-missing",
        "default-none",
        "default-non-mapping",
        "engine-missing",
        "name-missing",
        "engine-none",
        "name-none",
        "engine-blank",
        "name-blank",
    ],
)
def test_ready_health_rejects_invalid_database_configuration_before_dependency_checks(
    api_client,
    databases,
):
    api_client.raise_request_exception = False

    with patch.object(settings, "DATABASES", databases), patch.object(
        connection,
        "ensure_connection",
        side_effect=AssertionError("database check must be skipped"),
    ) as ensure_connection, patch(
        "django.db.migrations.executor.MigrationExecutor.migration_plan",
        side_effect=AssertionError("schema check must be skipped"),
    ) as migration_plan:
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 503
    assert response.data == {
        "code": "service_not_ready",
        "message": "service is not ready",
        "data": {
            "status": "not_ready",
            "failed_check": "configuration",
            "reason_code": "configuration_invalid",
            "checks": {
                "configuration": "invalid",
                "database": "unknown",
                "schema": "unknown",
            },
        },
    }
    ensure_connection.assert_not_called()
    migration_plan.assert_not_called()


def test_ready_health_reports_database_unavailable_without_leaking_exception(api_client):
    sensitive_error = OperationalError(
        "mysql://private_user:private_password@internal-db:3306/private_db SQL=SELECT secret"
    )
    with patch.object(connection, "ensure_connection", side_effect=sensitive_error), patch(
        "django.db.migrations.executor.MigrationExecutor.migration_plan",
        side_effect=AssertionError("schema check must be skipped"),
    ):
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 503
    assert response.data["data"] == {
        "status": "not_ready",
        "failed_check": "database",
        "reason_code": "database_unavailable",
        "checks": {
            "configuration": "valid",
            "database": "unavailable",
            "schema": "unknown",
        },
    }
    serialized = response.content.decode("utf-8")
    for forbidden in ["private_user", "private_password", "internal-db", "private_db", "SELECT"]:
        assert forbidden not in serialized


def test_ready_health_reports_schema_not_ready_without_migration_names(api_client):
    migration_name = "0005_private_schema_details"
    pending_migration = (type("Migration", (), {"name": migration_name})(), False)

    with patch(
        "django.db.migrations.executor.MigrationExecutor.migration_plan",
        return_value=[pending_migration],
    ):
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 503
    assert response.data["data"] == {
        "status": "not_ready",
        "failed_check": "schema",
        "reason_code": "schema_not_ready",
        "checks": {
            "configuration": "valid",
            "database": "available",
            "schema": "not_ready",
        },
    }
    assert migration_name not in response.content.decode("utf-8")


def test_ready_health_reports_database_unavailable_if_schema_check_loses_connection(api_client):
    sensitive_error = OperationalError("private_user@internal-db schema query failed")

    with patch(
        "common.health.MigrationExecutor",
        side_effect=sensitive_error,
    ):
        response = api_client.get("/api/v1/health/ready/")

    assert response.status_code == 503
    assert response.data["data"]["failed_check"] == "database"
    assert response.data["data"]["reason_code"] == "database_unavailable"
    assert response.data["data"]["checks"] == {
        "configuration": "valid",
        "database": "unavailable",
        "schema": "unknown",
    }
    serialized = response.content.decode("utf-8")
    assert "private_user" not in serialized
    assert "internal-db" not in serialized


def test_openapi_schema_documents_public_health_contracts(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    paths = response.data["paths"]
    live_get = paths["/api/v1/health/live/"]["get"]
    ready_get = paths["/api/v1/health/ready/"]["get"]

    assert set(live_get["responses"]) == {"200"}
    assert {"200", "503"}.issubset(ready_get["responses"])
    assert not live_get.get("security")
    assert not ready_get.get("security")

    schemas = response.data["components"]["schemas"]
    live_schema_name = live_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit(
        "/", 1
    )[-1]
    ready_schema_name = ready_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].rsplit(
        "/", 1
    )[-1]
    not_ready_schema_name = ready_get["responses"]["503"]["content"]["application/json"]["schema"]["$ref"].rsplit(
        "/", 1
    )[-1]

    assert {"code", "message", "data"}.issubset(schemas[live_schema_name]["properties"])
    assert {"code", "message", "data"}.issubset(schemas[ready_schema_name]["properties"])
    assert {"code", "message", "data"}.issubset(schemas[not_ready_schema_name]["properties"])
