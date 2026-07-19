from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import IntegrityError
from django.test import override_settings

from metrics.models import JenkinsTask, TestEnvironment, TestModule, TestRun


def catalog_service_module():
    """延迟导入，确保 RED 阶段缺少服务时由测试断言捕获。"""
    return importlib.import_module("metrics.environment_catalog")


def create_environment(*, env_key: str, base_url: str, is_active: bool = True) -> TestEnvironment:
    return TestEnvironment.objects.create(
        env_key=env_key,
        env_name=f"{env_key} 环境",
        base_url=base_url,
        url_desc=f"{env_key} 的测试环境",
        is_active=is_active,
    )


def create_module() -> TestModule:
    return TestModule.objects.create(
        package_name="stage13-package",
        case_path="test_case/stage13-package",
        module_name="Stage13 模块",
        module_dev="开发",
        module_test="测试",
    )


def catalog_entry(*, base_url: str, url_name: str, url_desc: str) -> dict[str, str]:
    return {
        "base_url": base_url,
        "url_name": url_name,
        "url_desc": url_desc,
    }


@pytest.mark.django_db
def test_environment_description_and_normalized_url_are_required_and_globally_unique():
    environment = create_environment(
        env_key="catalog-qa",
        base_url="https://catalog-qa.example.invalid/api/",
    )

    assert environment.url_desc == "catalog-qa 的测试环境"
    assert environment.base_url == "https://catalog-qa.example.invalid/api"
    with pytest.raises(IntegrityError):
        create_environment(
            env_key="catalog-duplicate",
            base_url="https://catalog-qa.example.invalid/api",
        )


@pytest.mark.django_db
def test_only_daily_full_test_run_allows_an_empty_module():
    environment = create_environment(
        env_key="run-qa",
        base_url="https://run-qa.example.invalid",
    )

    TestRun.objects.create(
        run_key="daily-full-parent",
        run_type=TestRun.RunType.DAILY_FULL,
        environment=environment,
    )
    with pytest.raises(IntegrityError):
        TestRun.objects.create(
            run_key="module-rerun-without-module",
            run_type=TestRun.RunType.MODULE_RERUN,
            environment=environment,
        )


@pytest.mark.django_db
def test_only_daily_full_jenkins_task_allows_an_empty_module():
    environment = create_environment(
        env_key="task-qa",
        base_url="https://task-qa.example.invalid",
    )
    module = create_module()

    JenkinsTask.objects.create(
        environment=environment,
        module=None,
        task_type=TestRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        build_number=101,
    )
    with pytest.raises(IntegrityError):
        JenkinsTask.objects.create(
            environment=environment,
            module=None,
            task_type=TestRun.RunType.FAILED_RERUN,
            job_full_name="AiApiTest-DWP-Failed-Rerun",
            build_number=102,
        )
    assert module.pk is not None


@pytest.mark.django_db
def test_mysql_to_yaml_attempt_freezes_active_catalog_and_rejects_another_active_attempt():
    service = catalog_service_module()
    create_environment(env_key="active-qa", base_url="https://active-qa.example.invalid", is_active=True)
    create_environment(env_key="inactive-qa", base_url="https://inactive-qa.example.invalid", is_active=False)
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )

    attempt = service.create_mysql_to_yaml_sync_attempt()

    assert attempt.direction == attempt.Direction.MYSQL_TO_YAML
    assert attempt.status == attempt.Status.PENDING
    assert attempt.expected_yaml_blob_sha == "a" * 40
    assert attempt.payload_json == {
        "active-qa": catalog_entry(
            base_url="https://active-qa.example.invalid",
            url_name="active-qa 环境",
            url_desc="active-qa 的测试环境",
        )
    }
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert state.status == state.Status.PENDING
    with pytest.raises(service.EnvironmentCatalogBusyError):
        service.create_yaml_to_mysql_sync_attempt()


@pytest.mark.django_db
def test_environment_creation_and_mysql_to_yaml_request_commit_together():
    service = catalog_service_module()
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )

    environment, attempt = service.create_environment_with_sync(
        env_key="created-qa",
        url_name="创建环境",
        base_url="https://created-qa.example.invalid/api/",
        url_desc="创建后的环境描述",
    )

    assert environment.base_url == "https://created-qa.example.invalid/api"
    assert TestEnvironment.objects.filter(pk=environment.pk).exists()
    assert attempt.payload_json == {
        "created-qa": catalog_entry(
            base_url="https://created-qa.example.invalid/api",
            url_name="创建环境",
            url_desc="创建后的环境描述",
        )
    }


@pytest.mark.django_db
def test_environment_edit_deactivate_and_restore_each_create_a_new_sync_attempt():
    service = catalog_service_module()
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    environment = create_environment(env_key="lifecycle-qa", base_url="https://lifecycle-qa.example.invalid")
    create_environment(env_key="lifecycle-support", base_url="https://lifecycle-support.example.invalid")

    edited, edit_attempt = service.update_environment_with_sync(
        environment,
        url_name="编辑后的环境",
        base_url="https://lifecycle-v2.example.invalid/api/",
        url_desc="编辑后的描述",
        is_active=False,
    )
    service.fail_sync_attempt(edit_attempt, error_code="jenkins_unavailable", error_summary="Jenkins unavailable")
    restored, restore_attempt = service.set_environment_active_with_sync(edited, is_active=True)

    assert edited.env_key == "lifecycle-qa"
    assert edited.base_url == "https://lifecycle-v2.example.invalid/api"
    assert edited.is_active is False
    assert list(edit_attempt.payload_json) == ["lifecycle-support"]
    assert restored.is_active is True
    assert restore_attempt.pk != edit_attempt.pk
    assert list(restore_attempt.payload_json) == ["lifecycle-qa", "lifecycle-support"]
    assert restore_attempt.payload_json["lifecycle-qa"] == catalog_entry(
        base_url="https://lifecycle-v2.example.invalid/api",
        url_name="编辑后的环境",
        url_desc="编辑后的描述",
    )


@pytest.mark.django_db
def test_delete_service_rejects_deactivating_the_last_active_environment_without_side_effects():
    service = catalog_service_module()
    state = service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    environment = create_environment(env_key="last-delete", base_url="https://last-delete.example.invalid")

    with pytest.raises(service.EnvironmentCatalogValidationError) as raised:
        service.set_environment_active_with_sync(environment, is_active=False)

    assert raised.value.code == "last_active_environment"
    environment.refresh_from_db()
    state.refresh_from_db()
    assert environment.is_active is True
    assert state.status == state.Status.SYNCED
    assert service.EnvironmentCatalogSyncAttempt.objects.count() == 0


@pytest.mark.django_db
def test_patch_service_rejects_deactivating_the_last_active_environment_without_side_effects():
    service = catalog_service_module()
    state = service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    environment = create_environment(env_key="last-patch", base_url="https://last-patch.example.invalid")

    with pytest.raises(service.EnvironmentCatalogValidationError) as raised:
        service.update_environment_with_sync(
            environment,
            url_name="不应保存的名称",
            base_url="https://last-patch-v2.example.invalid/api",
            url_desc="不应保存的描述",
            is_active=False,
        )

    assert raised.value.code == "last_active_environment"
    environment.refresh_from_db()
    state.refresh_from_db()
    assert environment.env_name == "last-patch 环境"
    assert environment.base_url == "https://last-patch.example.invalid"
    assert environment.url_desc == "last-patch 的测试环境"
    assert environment.is_active is True
    assert state.status == state.Status.SYNCED
    assert service.EnvironmentCatalogSyncAttempt.objects.count() == 0


@pytest.mark.django_db
def test_yaml_import_applies_create_update_and_logical_deactivation_atomically():
    service = catalog_service_module()
    create_environment(env_key="keep", base_url="https://keep.example.invalid")
    create_environment(env_key="update", base_url="https://old.example.invalid")
    retired = create_environment(env_key="retire", base_url="https://retire.example.invalid")

    result = service.apply_yaml_catalog_import(
        {
            "keep": catalog_entry(
                base_url="https://keep.example.invalid/",
                url_name="保留环境",
                url_desc="保留描述",
            ),
            "update": catalog_entry(
                base_url="https://updated.example.invalid/api/",
                url_name="更新环境",
                url_desc="更新描述",
            ),
            "new": catalog_entry(
                base_url="https://new.example.invalid/api",
                url_name="新增环境",
                url_desc="新增描述",
            ),
        }
    )

    assert result.created_count == 1
    assert result.updated_count == 2
    assert result.deactivated_count == 1
    assert TestEnvironment.objects.get(env_key="update").base_url == "https://updated.example.invalid/api"
    assert TestEnvironment.objects.get(env_key="update").url_desc == "更新描述"
    assert TestEnvironment.objects.get(env_key="new").is_active is True
    retired.refresh_from_db()
    assert retired.is_active is False


@pytest.mark.django_db
def test_yaml_import_callback_updates_projection_and_catalog_blob_sha():
    service = catalog_service_module()
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-import")
    service.mark_sync_attempt_running(attempt, build_number=103, jenkins_build_url="")

    completed, result = service.complete_yaml_to_mysql_sync_attempt(
        attempt,
        catalog={
            "imported-qa": catalog_entry(
                base_url="https://imported-qa.example.invalid/api/",
                url_name="导入环境",
                url_desc="从 YAML 导入",
            )
        },
        observed_yaml_blob_sha="b" * 40,
    )

    assert completed.status == completed.Status.SYNCED
    assert result.created_count == 1
    assert TestEnvironment.objects.get(env_key="imported-qa").base_url == "https://imported-qa.example.invalid/api"
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert state.status == state.Status.SYNCED
    assert state.yaml_blob_sha == "b" * 40


@pytest.mark.django_db
def test_invalid_yaml_callback_marks_running_attempt_failed_without_projection_and_allows_retry():
    service = catalog_service_module()
    baseline_environment = create_environment(env_key="callback-baseline", base_url="https://callback-baseline.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-invalid-import")
    service.mark_sync_attempt_running(attempt, build_number=104, jenkins_build_url="")

    with pytest.raises(service.EnvironmentCatalogValidationError) as raised:
        service.complete_yaml_to_mysql_sync_attempt(
            attempt,
            catalog={
                "invalid": {
                    "base_url": "https://invalid.example.invalid",
                    "url_name": "非法导入",
                    "url_desc": "不应投影",
                    "secret_hint": "must-not-persist",
                }
            },
            observed_yaml_blob_sha="b" * 40,
        )

    assert raised.value.code == "unknown_environment_field"
    attempt.refresh_from_db()
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    baseline_environment.refresh_from_db()
    assert attempt.status == attempt.Status.FAILED
    assert attempt.error_code == "unknown_environment_field"
    assert attempt.finished_at is not None
    assert attempt.active_attempt_key is None
    assert state.status == state.Status.FAILED
    assert state.last_error_code == "unknown_environment_field"
    assert baseline_environment.is_active is True
    assert TestEnvironment.objects.count() == 1
    retry_attempt = service.retry_sync_attempt(attempt)
    assert retry_attempt.status == retry_attempt.Status.PENDING


@pytest.mark.django_db
def test_mysql_to_yaml_callback_rejects_a_running_yaml_to_mysql_attempt_without_side_effects():
    service = catalog_service_module()
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-wrong-direction")
    service.mark_sync_attempt_running(attempt, build_number=105, jenkins_build_url="")

    with pytest.raises(service.EnvironmentCatalogStateError):
        service.complete_mysql_to_yaml_sync_attempt(
            attempt,
            observed_yaml_blob_sha="a" * 40,
            written_yaml_blob_sha="b" * 40,
            commit_sha="c" * 40,
        )

    attempt.refresh_from_db()
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert attempt.status == attempt.Status.RUNNING
    assert attempt.observed_yaml_blob_sha is None
    assert attempt.finished_at is None
    assert state.status == state.Status.RUNNING
    assert state.yaml_blob_sha == "a" * 40


@pytest.mark.django_db
def test_successful_yaml_callback_is_idempotent_without_reprojecting_environments():
    service = catalog_service_module()
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-idempotent-import")
    service.mark_sync_attempt_running(attempt, build_number=106, jenkins_build_url="")
    catalog = {
        "idempotent-qa": catalog_entry(
            base_url="https://idempotent-qa.example.invalid/api",
            url_name="幂等导入环境",
            url_desc="幂等导入描述",
        )
    }

    completed, first_result = service.complete_yaml_to_mysql_sync_attempt(
        attempt,
        catalog=catalog,
        observed_yaml_blob_sha="b" * 40,
    )
    environment = TestEnvironment.objects.get(env_key="idempotent-qa")
    environment_updated_at = environment.updated_at
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    state_updated_at = state.updated_at

    repeated, repeated_result = service.complete_yaml_to_mysql_sync_attempt(
        completed,
        catalog=catalog,
        observed_yaml_blob_sha="b" * 40,
    )

    environment.refresh_from_db()
    state.refresh_from_db()
    assert first_result.created_count == 1
    assert repeated.pk == completed.pk
    assert repeated_result == service.CatalogImportResult(0, 0, 0)
    assert TestEnvironment.objects.count() == 1
    assert environment.updated_at == environment_updated_at
    assert state.updated_at == state_updated_at


@pytest.mark.django_db
def test_yaml_import_callback_allows_existing_environments_to_swap_base_urls():
    service = catalog_service_module()
    first = create_environment(env_key="swap-first", base_url="https://swap-first.example.invalid")
    second = create_environment(env_key="swap-second", base_url="https://swap-second.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-swap-base-url")
    service.mark_sync_attempt_running(attempt, build_number=107, jenkins_build_url="")

    completed, result = service.complete_yaml_to_mysql_sync_attempt(
        attempt,
        catalog={
            "swap-first": catalog_entry(
                base_url="https://swap-second.example.invalid",
                url_name="互换后环境一",
                url_desc="互换后描述一",
            ),
            "swap-second": catalog_entry(
                base_url="https://swap-first.example.invalid",
                url_name="互换后环境二",
                url_desc="互换后描述二",
            ),
        },
        observed_yaml_blob_sha="b" * 40,
    )

    first.refresh_from_db()
    second.refresh_from_db()
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert result == service.CatalogImportResult(0, 2, 0)
    assert first.base_url == "https://swap-second.example.invalid"
    assert second.base_url == "https://swap-first.example.invalid"
    assert completed.status == completed.Status.SYNCED
    assert state.status == state.Status.SYNCED


@pytest.mark.django_db
def test_yaml_import_persistence_error_marks_attempt_failed_without_partial_projection_and_allows_retry(monkeypatch):
    service = catalog_service_module()
    existing = create_environment(env_key="persistence-existing", base_url="https://persistence-existing.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_yaml_to_mysql_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-persistence-error")
    service.mark_sync_attempt_running(attempt, build_number=108, jenkins_build_url="")
    original_save = service.TestEnvironment.save

    def raise_on_new_environment_save(environment, *args, **kwargs):
        if environment.env_key == "persistence-new":
            raise IntegrityError("database failure detail must not be exposed")
        return original_save(environment, *args, **kwargs)

    monkeypatch.setattr(service.TestEnvironment, "save", raise_on_new_environment_save)

    with pytest.raises(service.EnvironmentCatalogError) as raised:
        service.complete_yaml_to_mysql_sync_attempt(
            attempt,
            catalog={
                "persistence-existing": catalog_entry(
                    base_url="https://persistence-existing-updated.example.invalid",
                    url_name="更新后环境",
                    url_desc="更新后描述",
                ),
                "persistence-new": catalog_entry(
                    base_url="https://persistence-new.example.invalid",
                    url_name="新增环境",
                    url_desc="新增环境描述",
                ),
            },
            observed_yaml_blob_sha="b" * 40,
        )

    existing.refresh_from_db()
    attempt.refresh_from_db()
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert raised.value.code == "environment_catalog_projection_failed"
    assert "database failure detail" not in str(raised.value)
    assert existing.base_url == "https://persistence-existing.example.invalid"
    assert existing.env_name == "persistence-existing 环境"
    assert TestEnvironment.objects.filter(env_key="persistence-new").exists() is False
    assert attempt.status == attempt.Status.FAILED
    assert attempt.error_code == "environment_catalog_projection_failed"
    assert attempt.error_summary == "环境目录投影失败，请修正后重试。"
    assert attempt.active_attempt_key is None
    assert state.status == state.Status.FAILED
    assert state.last_error_code == "environment_catalog_projection_failed"
    assert service.retry_sync_attempt(attempt).status == attempt.Status.PENDING


@pytest.mark.django_db
def test_yaml_import_rejects_a_synced_mysql_to_yaml_attempt_without_side_effects():
    service = catalog_service_module()
    create_environment(env_key="synced-wrong-direction", base_url="https://synced-wrong-direction.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_mysql_to_yaml_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-synced-wrong-direction")
    service.mark_sync_attempt_running(attempt, build_number=109, jenkins_build_url="")
    completed = service.complete_mysql_to_yaml_sync_attempt(
        attempt,
        observed_yaml_blob_sha="a" * 40,
        written_yaml_blob_sha="b" * 40,
        commit_sha="c" * 40,
    )
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    state_updated_at = state.updated_at

    with pytest.raises(service.EnvironmentCatalogStateError):
        service.complete_yaml_to_mysql_sync_attempt(
            completed,
            catalog={"unexpected": catalog_entry(
                base_url="https://unexpected.example.invalid",
                url_name="不应导入",
                url_desc="错误方向",
            )},
            observed_yaml_blob_sha="b" * 40,
        )

    completed.refresh_from_db()
    state.refresh_from_db()
    assert completed.status == completed.Status.SYNCED
    assert state.status == state.Status.SYNCED
    assert state.updated_at == state_updated_at
    assert TestEnvironment.objects.filter(env_key="unexpected").exists() is False


def test_environment_url_migration_validates_all_rows_before_persisting_any_update():
    migration = importlib.import_module("metrics.migrations.0005_stage13_environment_catalog")
    first = type("HistoricalEnvironment", (), {"id": 1, "base_url": "https://first.example.invalid/"})()
    second = type("HistoricalEnvironment", (), {"id": 2, "base_url": "not-a-valid-url"})()
    updates: list[tuple[int, dict[str, str]]] = []

    class FakeObjects:
        def order_by(self, *args):
            return self

        def iterator(self):
            return iter([first, second])

        def filter(self, *, pk: int):
            class FakeUpdate:
                def update(self, **values):
                    updates.append((pk, values))

            return FakeUpdate()

    class FakeHistoricalEnvironment:
        objects = FakeObjects()

    class FakeApps:
        @staticmethod
        def get_model(app_label: str, model_name: str):
            assert (app_label, model_name) == ("metrics", "TestEnvironment")
            return FakeHistoricalEnvironment

    with pytest.raises(RuntimeError, match="非法测试环境 URL"):
        migration.normalize_existing_environment_urls(FakeApps(), None)

    assert first.base_url == "https://first.example.invalid/"
    assert updates == []


@pytest.mark.django_db
def test_invalid_yaml_catalog_projection_has_zero_database_side_effects():
    service = catalog_service_module()
    create_environment(env_key="baseline", base_url="https://baseline.example.invalid")
    baseline = list(TestEnvironment.objects.values("env_key", "base_url", "is_active"))

    with pytest.raises(service.EnvironmentCatalogValidationError) as raised:
        service.apply_yaml_catalog_import(
            {
                "broken": {
                    "base_url": "https://broken.example.invalid",
                    "url_name": "损坏环境",
                    "url_desc": "损坏描述",
                    "secret_hint": "must-not-persist",
                }
            }
        )

    assert raised.value.code == "unknown_environment_field"
    assert list(TestEnvironment.objects.values("env_key", "base_url", "is_active")) == baseline
    assert service.EnvironmentCatalogState.objects.count() == 0
    assert service.EnvironmentCatalogSyncAttempt.objects.count() == 0


@pytest.mark.django_db
def test_blob_sha_conflict_is_recorded_and_cannot_be_retried_directly():
    service = catalog_service_module()
    create_environment(env_key="conflict-qa", base_url="https://conflict-qa.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_mysql_to_yaml_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-101")
    service.mark_sync_attempt_running(
        attempt,
        build_number=101,
        jenkins_build_url="https://jenkins.example.invalid/job/catalog/101/",
    )

    conflicted = service.complete_mysql_to_yaml_sync_attempt(
        attempt,
        observed_yaml_blob_sha="b" * 40,
        written_yaml_blob_sha="c" * 40,
        commit_sha="d" * 40,
    )

    assert conflicted.status == conflicted.Status.CONFLICT
    assert conflicted.observed_yaml_blob_sha == "b" * 40
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert state.status == state.Status.CONFLICT
    assert state.yaml_blob_sha == "a" * 40
    with pytest.raises(service.EnvironmentCatalogSyncNotRetryableError):
        service.retry_sync_attempt(conflicted)


@pytest.mark.django_db
def test_sync_attempt_progresses_to_synced_after_a_matching_callback():
    service = catalog_service_module()
    create_environment(env_key="synced-qa", base_url="https://synced-qa.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    attempt = service.create_mysql_to_yaml_sync_attempt()
    service.mark_sync_attempt_queued(attempt, queue_id="queue-102")
    service.mark_sync_attempt_running(attempt, build_number=102, jenkins_build_url="")

    completed = service.complete_mysql_to_yaml_sync_attempt(
        attempt,
        observed_yaml_blob_sha="a" * 40,
        written_yaml_blob_sha="b" * 40,
        commit_sha="c" * 40,
    )

    assert completed.status == completed.Status.SYNCED
    state = service.EnvironmentCatalogState.objects.get(catalog_key=service.CATALOG_KEY)
    assert state.status == state.Status.SYNCED
    assert state.yaml_blob_sha == "b" * 40
    assert state.last_commit_sha == "c" * 40


@pytest.mark.django_db
def test_failed_sync_creates_a_new_immutable_retry_attempt():
    service = catalog_service_module()
    create_environment(env_key="retry-qa", base_url="https://retry-qa.example.invalid")
    service.EnvironmentCatalogState.objects.create(
        catalog_key=service.CATALOG_KEY,
        yaml_blob_sha="a" * 40,
        status=service.EnvironmentCatalogState.Status.SYNCED,
    )
    failed_attempt = service.create_mysql_to_yaml_sync_attempt()
    service.fail_sync_attempt(failed_attempt, error_code="git_push_failed", error_summary="Git push failed")

    retry_attempt = service.retry_sync_attempt(failed_attempt)

    assert retry_attempt.pk != failed_attempt.pk
    assert retry_attempt.status == retry_attempt.Status.PENDING
    assert retry_attempt.direction == failed_attempt.direction
    assert retry_attempt.payload_json == failed_attempt.payload_json
    assert retry_attempt.payload_sha256 == failed_attempt.payload_sha256


@pytest.mark.django_db
def test_seed_environment_uses_image_catalog_instead_of_a_hard_coded_environment(tmp_path):
    catalog_path = tmp_path / "api-test" / "utils" / "package_environment.yaml"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(
        """bootstrap-qa:
  base_url: https://bootstrap-qa.example.invalid/api/
  url_name: Bootstrap QA
  url_desc: 镜像内初始化环境
""",
        encoding="utf-8",
    )

    with override_settings(REPO_ROOT=Path(tmp_path)):
        call_command("seed_environment")
        call_command("seed_environment")

    assert TestEnvironment.objects.count() == 1
    environment = TestEnvironment.objects.get(env_key="bootstrap-qa")
    assert environment.base_url == "https://bootstrap-qa.example.invalid/api"
    assert environment.env_name == "Bootstrap QA"
    assert environment.url_desc == "镜像内初始化环境"


def test_backend_image_copies_the_environment_catalog_build_input():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY api-test/utils/package_environment.yaml" in dockerfile
