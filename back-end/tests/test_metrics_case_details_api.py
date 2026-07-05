from __future__ import annotations

import hashlib
import importlib

import pytest
from django.db import IntegrityError, transaction
from django.db import migrations

from tests.p3_metrics_helpers import create_case_result, create_p3_metric_context
from tests.p3_metrics_helpers import metric_model


pytestmark = pytest.mark.api


@pytest.fixture
def p3_context(db) -> dict:
    context = create_p3_metric_context()
    create_case_result(context, display_status="failed", node_suffix="search_species")
    create_case_result(context, display_status="passed", node_suffix="get_species")
    create_case_result(context, display_status="skipped", node_suffix="legacy_species")
    return context


def test_case_details_default_failed_filter_returns_admin_detail(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 200
    assert response.data["meta"] == {"total": 1, "page": 1, "per_page": 20, "total_pages": 1}
    row = response.data["data"][0]
    assert row["case_name"] == "test_search_species"
    assert row["display_status"] == "failed"
    assert row["error_type"] == "AssertionError"
    assert row["error_message_summary"] == "AssertionError: expected 200, got 500"
    assert row["error_message_detail"]
    assert "demo-token" not in row["error_message_detail"]
    assert "password=demo" not in row["error_message_detail"]
    assert "sessionid=secret" not in row["error_message_detail"]
    assert "10.0.0.5" not in row["error_message_detail"]
    assert row["actions"] == {"can_update_status": True, "can_retry": False}


@pytest.mark.parametrize(
    ("status_value", "expected_case"),
    [
        ("passed", "test_get_species"),
        ("skipped", "test_legacy_species"),
    ],
)
def test_case_details_filter_by_passed_and_skipped(admin_client, p3_context, status_value, expected_case):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases", {"status": status_value})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["case_name"] == expected_case
    assert response.data["data"][0]["display_status"] == status_value


def test_case_details_member_only_receives_summary(member_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = member_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["error_message_summary"]
    assert row["error_message_detail"] is None
    assert row["actions"] == {"can_update_status": False, "can_retry": False}


def test_case_details_supports_query_filters(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(
        f"/api/v1/module-snapshots/{snapshot.id}/cases",
        {"status": "failed", "case_name": "search", "node_id": "species.py", "error_type": "AssertionError"},
    )

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["case_name"] == "test_search_species"


@pytest.mark.parametrize(
    "params",
    [
        {"status": "archived"},
        {"page": "0"},
        {"per_page": "101"},
        {"case_name": "x" * 257},
        {"node_id": "x" * 1025},
        {"error_type": "x" * 129},
    ],
)
def test_case_details_rejects_invalid_query_params(admin_client, p3_context, params):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases", params)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_case_details_unknown_snapshot_returns_404(admin_client):
    response = admin_client.get("/api/v1/module-snapshots/999999/cases")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_case_details_inactive_environment_snapshot_returns_404(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]
    environment = p3_context["environment"]
    environment.is_active = False
    environment.save(update_fields=["is_active", "updated_at"])

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_case_details_requires_login(api_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = api_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "authentication_required"


def test_current_case_result_is_unique_by_environment_module_and_node_id(p3_context):
    existing = create_case_result(p3_context, display_status="failed", node_suffix="unique_case")
    assert existing.current_node_key == hashlib.sha256(existing.node_id.encode("utf-8")).hexdigest()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_case_result(p3_context, display_status="failed", node_suffix="unique_case")

    archived_copy = create_case_result(
        p3_context,
        display_status="failed",
        node_suffix="unique_case",
        is_current=False,
    )
    assert archived_copy.node_id == existing.node_id
    assert archived_copy.current_node_key is None


def test_current_case_result_unique_constraint_is_mysql_compatible():
    TestCaseResult = metric_model("TestCaseResult")

    constraints = {constraint.name: constraint for constraint in TestCaseResult._meta.constraints}
    current_unique = constraints["uniq_current_case_result_env_module_node"]
    assert tuple(current_unique.fields) == ("environment", "module", "current_node_key")
    assert current_unique.condition is None
    assert TestCaseResult._meta.get_field("current_node_key").max_length == 64
    assert TestCaseResult._meta.get_field("node_id").db_index is False


def test_case_result_key_followup_migration_rehashes_existing_rows_before_alter():
    migration_module = importlib.import_module("metrics.migrations.0004_hash_case_result_current_node_key")
    operation_types = [type(operation) for operation in migration_module.Migration.operations]

    assert operation_types[:4] == [migrations.RunPython, migrations.RunPython, migrations.AlterField, migrations.AlterField]
    assert migration_module.Migration.operations[0].code is migration_module.hash_existing_current_node_keys
    assert migration_module.Migration.operations[1].code is migration_module.apply_legacy_mysql_schema_changes


def test_case_result_key_followup_migration_repairs_legacy_mysql_schema():
    migration_module = importlib.import_module("metrics.migrations.0004_hash_case_result_current_node_key")

    class FakeCursor:
        def __init__(self):
            self.queries: list[tuple[str, list[str] | None]] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, sql, params=None):
            self.queries.append((sql, params))

        def fetchone(self):
            return [1024]

    class FakeIntrospection:
        def get_constraints(self, cursor, table_name):
            return {
                "test_case_result_node_id_legacy_idx": {
                    "columns": ["node_id"],
                    "index": True,
                    "unique": False,
                    "primary_key": False,
                    "foreign_key": None,
                },
                "uniq_current_case_result_env_module_node": {
                    "columns": ["environment_id", "module_id", "current_node_key"],
                    "index": True,
                    "unique": True,
                    "primary_key": False,
                    "foreign_key": None,
                },
            }

    class FakeConnection:
        vendor = "mysql"
        introspection = FakeIntrospection()

        def __init__(self):
            self.cursor_obj = FakeCursor()

        def cursor(self):
            return self.cursor_obj

    class FakeSchemaEditor:
        def __init__(self):
            self.connection = FakeConnection()
            self.executed_sql: list[str] = []

        def quote_name(self, name):
            return f"`{name}`"

        def execute(self, sql):
            self.executed_sql.append(sql)

    schema_editor = FakeSchemaEditor()

    migration_module.apply_legacy_mysql_schema_changes(None, schema_editor)

    assert any("MODIFY `current_node_key` varchar(64) NULL" in sql for sql in schema_editor.executed_sql)
    assert any("DROP INDEX `test_case_result_node_id_legacy_idx`" in sql for sql in schema_editor.executed_sql)
