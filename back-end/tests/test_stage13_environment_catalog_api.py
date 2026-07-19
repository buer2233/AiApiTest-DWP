from __future__ import annotations

import importlib

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from metrics.models import EnvironmentCatalogState, EnvironmentCatalogSyncAttempt, TestEnvironment as MetricEnvironment
from tests.conftest import TEST_PASSWORD


pytestmark = pytest.mark.api

INITIAL_YAML_BLOB_SHA = "a" * 40


def catalog_service():
    return importlib.import_module("metrics.environment_catalog")


def create_environment(*, env_key: str, is_active: bool = True) -> MetricEnvironment:
    return MetricEnvironment.objects.create(
        env_key=env_key,
        env_name=f"{env_key} 环境",
        base_url=f"https://{env_key}.example.invalid/api",
        url_desc=f"{env_key} 的测试环境",
        is_active=is_active,
    )


def login_client(user) -> APIClient:
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login",
        {"username": user.username, "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def catalog_state(db) -> EnvironmentCatalogState:
    return EnvironmentCatalogState.objects.create(
        catalog_key=EnvironmentCatalogState.CATALOG_KEY,
        yaml_blob_sha=INITIAL_YAML_BLOB_SHA,
        status=EnvironmentCatalogState.Status.SYNCED,
    )


@pytest.mark.django_db
def test_member_lists_only_active_environments_with_catalog_state(member_client, catalog_state):
    active = create_environment(env_key="stage13-active")
    inactive = create_environment(env_key="stage13-inactive", is_active=False)

    response = member_client.get("/api/v1/test-environments", {"is_active": "false"})

    assert response.status_code == 200
    assert [item["id"] for item in response.data["data"]] == [active.id]
    assert response.data["catalog_state"] == {
        "status": "synced",
        "yaml_blob_sha": INITIAL_YAML_BLOB_SHA,
        "last_commit_sha": "",
        "last_synced_at": None,
        "last_error_code": "",
        "last_error_summary": "",
    }
    assert inactive.id not in [item["id"] for item in response.data["data"]]


@pytest.mark.django_db
def test_admin_crud_creates_immutable_sync_attempt_and_rejects_the_last_active_environment(
    admin_client,
    admin_user,
    catalog_state,
):
    existing = create_environment(env_key="stage13-existing")

    created = admin_client.post(
        "/api/v1/test-environments",
        {
            "env_key": "stage13-qa",
            "url_name": "Stage13 QA",
            "base_url": "https://stage13-qa.example.invalid/api/",
            "url_desc": "自动化回归测试环境",
        },
        format="json",
    )

    assert created.status_code == 202
    environment_data = created.data["data"]["environment"]
    assert environment_data["env_key"] == "stage13-qa"
    assert environment_data["url_name"] == "Stage13 QA"
    assert environment_data["env_name"] == "Stage13 QA"
    assert environment_data["base_url"] == "https://stage13-qa.example.invalid/api"
    assert environment_data["url_desc"] == "自动化回归测试环境"
    assert environment_data["is_active"] is True
    attempt_id = created.data["data"]["sync_attempt"]["id"]
    attempt = EnvironmentCatalogSyncAttempt.objects.get(id=attempt_id)
    assert attempt.direction == EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML
    assert attempt.status == EnvironmentCatalogSyncAttempt.Status.PENDING
    assert attempt.requested_by == admin_user
    assert attempt.payload_json["stage13-qa"]["base_url"] == "https://stage13-qa.example.invalid/api"
    assert created.data["data"]["sync_attempt"]["jenkins_build_url"] == ""

    active_before = MetricEnvironment.objects.filter(is_active=True).count()
    blocked = admin_client.delete(f"/api/v1/test-environments/{existing.id}")
    assert blocked.status_code == 409
    assert blocked.data["error"]["code"] == "environment_config_sync_busy"
    assert MetricEnvironment.objects.filter(is_active=True).count() == active_before

    catalog_service().fail_sync_attempt(
        attempt,
        error_code="jenkins_unavailable",
        error_summary="Jenkins unavailable",
    )
    removed = admin_client.delete(f"/api/v1/test-environments/{existing.id}")
    assert removed.status_code == 202
    existing.refresh_from_db()
    assert existing.is_active is False

    latest_attempt = EnvironmentCatalogSyncAttempt.objects.get(id=removed.data["data"]["sync_attempt"]["id"])
    catalog_service().fail_sync_attempt(
        latest_attempt,
        error_code="jenkins_unavailable",
        error_summary="Jenkins unavailable",
    )
    last_active = MetricEnvironment.objects.get(env_key="stage13-qa")
    rejected = admin_client.patch(
        f"/api/v1/test-environments/{last_active.id}",
        {"is_active": False},
        format="json",
    )
    assert rejected.status_code == 409
    assert rejected.data["error"]["code"] == "last_active_environment"
    last_active.refresh_from_db()
    assert last_active.is_active is True


@pytest.mark.django_db
def test_catalog_sync_attempt_audit_retry_and_member_permission_boundaries(
    admin_client,
    admin_user,
    member_user,
    catalog_state,
):
    create_environment(env_key="stage13-audit")
    attempt = catalog_service().create_mysql_to_yaml_sync_attempt(requested_by=admin_user)
    catalog_service().fail_sync_attempt(
        attempt,
        error_code="git_push_failed",
        error_summary="Git push failed",
    )
    attempt.jenkins_build_url = "https://ci.example.invalid/job/environment-catalog/41/"
    attempt.save(update_fields=["jenkins_build_url"])

    audit = admin_client.get(f"/api/v1/environment-catalog-sync-attempts/{attempt.id}")
    retried = admin_client.post(f"/api/v1/environment-catalog-sync-attempts/{attempt.id}/retry", {}, format="json")

    assert audit.status_code == 200
    assert audit.data["data"]["id"] == attempt.id
    assert audit.data["data"]["error_code"] == "git_push_failed"
    assert audit.data["data"]["jenkins_build_url"] == "https://ci.example.invalid/job/environment-catalog/41/"
    assert retried.status_code == 202
    assert retried.data["data"]["id"] != attempt.id
    assert retried.data["data"]["status"] == "pending"
    assert retried.data["data"]["jenkins_build_url"] == ""

    member_client = login_client(member_user)
    for response in [
        member_client.get(f"/api/v1/environment-catalog-sync-attempts/{attempt.id}"),
        member_client.post("/api/v1/test-environments/sync-from-yaml", {}, format="json"),
        member_client.post(f"/api/v1/environment-catalog-sync-attempts/{attempt.id}/retry", {}, format="json"),
    ]:
        assert response.status_code == 403
        assert response.data["error"]["code"] == "admin_required"


@pytest.mark.django_db
def test_internal_catalog_export_and_callback_require_service_token_and_use_service_state_machine(catalog_state):
    create_environment(env_key="stage13-internal")
    attempt = catalog_service().create_mysql_to_yaml_sync_attempt()
    catalog_service().mark_sync_attempt_queued(attempt, queue_id="queue-stage13")

    with override_settings(ENVIRONMENT_CATALOG_SERVICE_TOKEN="service-token-for-tests"):
        forbidden = pytest.importorskip("rest_framework.test").APIClient().get(
            f"/api/v1/internal/environment-catalog-sync-attempts/{attempt.request_id}/export/"
        )
        authorized_client = pytest.importorskip("rest_framework.test").APIClient()
        exported = authorized_client.get(
            f"/api/v1/internal/environment-catalog-sync-attempts/{attempt.request_id}/export/",
            HTTP_AUTHORIZATION="Bearer service-token-for-tests",
        )

        assert forbidden.status_code == 403
        assert exported.status_code == 200
        assert exported.data == attempt.payload_json
        attempt.refresh_from_db()
        assert attempt.status == EnvironmentCatalogSyncAttempt.Status.RUNNING

    assert EnvironmentCatalogState.objects.get().status == EnvironmentCatalogState.Status.RUNNING


@pytest.mark.django_db
def test_internal_yaml_import_callback_uses_service_state_machine_without_leaking_credentials(catalog_state):
    create_environment(env_key="stage13-yaml-existing")
    attempt = catalog_service().create_yaml_to_mysql_sync_attempt()
    catalog_service().mark_sync_attempt_queued(attempt, queue_id="queue-stage13-yaml")

    with override_settings(ENVIRONMENT_CATALOG_SERVICE_TOKEN="service-token-for-tests"):
        client = pytest.importorskip("rest_framework.test").APIClient()
        completed = client.post(
            f"/api/v1/internal/environment-catalog-sync-attempts/{attempt.request_id}/callback/",
            {
                "direction": "yaml_to_mysql",
                "expected_yaml_blob_sha": INITIAL_YAML_BLOB_SHA,
                "observed_yaml_blob_sha": "b" * 40,
                "catalog": {
                    "stage13-yaml-import": {
                        "base_url": "https://stage13-yaml-import.example.invalid/api",
                        "url_name": "Stage13 YAML Import",
                        "url_desc": "由隔离 checkout 导入",
                    }
                },
            },
            format="json",
            HTTP_AUTHORIZATION="Bearer service-token-for-tests",
        )

    assert completed.status_code == 200
    attempt.refresh_from_db()
    assert attempt.status == EnvironmentCatalogSyncAttempt.Status.SYNCED
    assert MetricEnvironment.objects.get(env_key="stage13-yaml-import").is_active is True
    assert "service-token-for-tests" not in str(completed.data)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("direction", "payload"),
    [
        (
            EnvironmentCatalogSyncAttempt.Direction.YAML_TO_MYSQL,
            {
                "direction": "yaml_to_mysql",
                "expected_yaml_blob_sha": INITIAL_YAML_BLOB_SHA,
                "observed_yaml_blob_sha": "b" * 40,
                "catalog": {},
                "unexpected": "field",
            },
        ),
        (
            EnvironmentCatalogSyncAttempt.Direction.MYSQL_TO_YAML,
            {
                "direction": "mysql_to_yaml",
                "expected_yaml_blob_sha": INITIAL_YAML_BLOB_SHA,
                "observed_yaml_blob_sha": "b" * 40,
            },
        ),
    ],
    ids=["yaml_unknown_field", "mysql_missing_required_field"],
)
def test_internal_callback_schema_error_fails_queued_attempt_and_allows_admin_retry(
    admin_client,
    catalog_state,
    direction,
    payload,
):
    create_environment(env_key=f"callback-{direction}")
    attempt_factory = (
        catalog_service().create_yaml_to_mysql_sync_attempt
        if direction == EnvironmentCatalogSyncAttempt.Direction.YAML_TO_MYSQL
        else catalog_service().create_mysql_to_yaml_sync_attempt
    )
    attempt = attempt_factory()
    catalog_service().mark_sync_attempt_queued(attempt, queue_id=f"queue-{direction}")

    with override_settings(ENVIRONMENT_CATALOG_SERVICE_TOKEN="service-token-for-tests"):
        callback = APIClient().post(
            f"/api/v1/internal/environment-catalog-sync-attempts/{attempt.request_id}/callback/",
            payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer service-token-for-tests",
        )

    assert callback.status_code == 400
    assert callback.data["error"]["code"] == "validation_error"
    attempt.refresh_from_db()
    assert attempt.status == EnvironmentCatalogSyncAttempt.Status.FAILED
    retry = admin_client.post(f"/api/v1/environment-catalog-sync-attempts/{attempt.id}/retry", {}, format="json")
    assert retry.status_code == 202
