from __future__ import annotations

import signal
from io import StringIO
from unittest.mock import call, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from metrics.models import (
    EnvironmentSnapshot,
    JenkinsJobBinding,
    ModuleSnapshot,
    TestEnvironment as MetricEnvironment,
    TestModule as MetricModule,
    TestRun as MetricRun,
)
from tests.p3_metrics_helpers import metric_model


pytestmark = pytest.mark.command


def write_module_yaml(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_case_file(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.django_db
def test_sync_modules_creates_updates_and_keeps_case_path_idempotent(tmp_path):
    yaml_path = tmp_path / "package_module.yaml"
    write_module_yaml(
        yaml_path,
        """
test_gbif_case:
  module_name: 示例模块1
  module_dev: 张三
  module_test: 王五
test_gbif_case_module2:
  module_name: 示例模块2
  module_dev: 赵四
  module_test: 王麻子
""",
    )

    stdout = StringIO()
    call_command("sync_modules", source=str(yaml_path), stdout=stdout)
    call_command("sync_modules", source=str(yaml_path), stdout=stdout)

    assert MetricModule.objects.count() == 2
    module = MetricModule.objects.get(package_name="test_gbif_case")
    assert module.module_name == "示例模块1"
    assert module.module_dev == "张三"
    assert module.module_test == "王五"
    assert module.case_path == "test_case/test_gbif_case"
    assert module.is_active is True
    assert "success=2" in stdout.getvalue()

    write_module_yaml(
        yaml_path,
        """
test_gbif_case:
  module_name: 示例模块1
  module_dev: 张三丰
  module_test: 王五
""",
    )
    call_command("sync_modules", source=str(yaml_path), stdout=stdout)

    module.refresh_from_db()
    assert module.module_dev == "张三丰"
    assert MetricModule.objects.count() == 2


@pytest.mark.django_db
def test_sync_modules_skips_missing_required_fields_and_reports_reason(tmp_path):
    yaml_path = tmp_path / "package_module.yaml"
    write_module_yaml(
        yaml_path,
        """
valid_case:
  module_name: 有效模块
  module_dev: 张三
  module_test: 王五
broken_case:
  module_name: 缺字段模块
  module_dev: 赵四
""",
    )

    stdout = StringIO()
    call_command("sync_modules", source=str(yaml_path), stdout=stdout)

    assert MetricModule.objects.filter(package_name="valid_case").exists()
    assert not MetricModule.objects.filter(package_name="broken_case").exists()
    output = stdout.getvalue()
    assert "broken_case" in output
    assert "module_test" in output
    assert "failed=1" in output


@pytest.mark.django_db
def test_sync_jenkins_job_bindings_upserts_retry_and_daily_jobs(monkeypatch):
    environment = MetricEnvironment.objects.create(
        env_key="mock-gbif",
        env_name="模拟测试环境",
        base_url="https://api.gbif.org",
        is_active=True,
    )
    module = MetricModule.objects.create(
        package_name="Species",
        case_path="test_case/Species",
        module_name="物种查询",
        module_dev="张三",
        module_test="王五",
        is_active=True,
    )
    MetricEnvironment.objects.create(
        env_key="inactive",
        env_name="停用环境",
        base_url="https://inactive.example.com",
        is_active=False,
    )
    MetricModule.objects.create(
        package_name="Inactive",
        case_path="test_case/Inactive",
        module_name="停用模块",
        module_dev="赵四",
        module_test="王麻子",
        is_active=False,
    )
    monkeypatch.setenv("JENKINS_FAILED_RERUN_JOB_NAME", "AiApiTest-DWP-Failed-Rerun")
    monkeypatch.setenv("JENKINS_MODULE_RERUN_JOB_NAME", "AiApiTest-DWP-Module-Rerun")
    monkeypatch.setenv("JENKINS_DAILY_FULL_JOB_NAME", "AiApiTest-DWP-Daily-Full-Module")
    monkeypatch.setenv("JENKINS_API_TOKEN", "secret-token-not-for-output")

    stdout = StringIO()
    call_command("sync_jenkins_job_bindings", stdout=stdout)
    call_command("sync_jenkins_job_bindings", stdout=stdout)

    bindings = JenkinsJobBinding.objects.filter(environment=environment, module=module, is_active=True)
    assert bindings.count() == 2
    assert bindings.get(task_type=MetricRun.RunType.FAILED_RERUN).job_full_name == "AiApiTest-DWP-Failed-Rerun"
    assert bindings.get(task_type=MetricRun.RunType.MODULE_RERUN).job_full_name == "AiApiTest-DWP-Module-Rerun"
    daily_binding = JenkinsJobBinding.objects.get(
        environment__isnull=True,
        module__isnull=True,
        task_type=MetricRun.RunType.DAILY_FULL,
    )
    assert daily_binding.job_full_name == "AiApiTest-DWP-Daily-Full-Module"
    assert JenkinsJobBinding.objects.filter(environment__env_key="inactive").count() == 0
    assert JenkinsJobBinding.objects.filter(module__package_name="Inactive").count() == 0
    output = stdout.getvalue()
    assert "created=3" in output
    assert "created=0" in output
    assert "skipped=" in output
    assert "secret-token-not-for-output" not in output


@pytest.mark.django_db
def test_sync_jenkins_job_bindings_keeps_only_one_active_global_daily_binding(monkeypatch):
    environment = MetricEnvironment.objects.create(
        env_key="daily-duplicate-environment",
        env_name="Daily 重复绑定环境",
        base_url="https://daily-duplicate.example.invalid",
        is_active=True,
    )
    module = MetricModule.objects.create(
        package_name="daily_duplicate_module",
        case_path="test_case/daily_duplicate_module",
        module_name="Daily 重复绑定模块",
        module_dev="开发",
        module_test="测试",
        is_active=True,
    )
    canonical = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="legacy-global-daily",
        is_active=True,
    )
    duplicate = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="duplicate-global-daily",
        is_active=True,
    )
    legacy_module_binding = JenkinsJobBinding.objects.create(
        environment=environment,
        module=module,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="legacy-module-daily",
        is_active=True,
    )
    monkeypatch.setenv("JENKINS_FAILED_RERUN_JOB_NAME", "")
    monkeypatch.setenv("JENKINS_MODULE_RERUN_JOB_NAME", "")
    monkeypatch.setenv("JENKINS_DAILY_FULL_JOB_NAME", "AiApiTest-DWP-Daily-Full-Module")

    call_command("sync_jenkins_job_bindings", stdout=StringIO())

    canonical.refresh_from_db()
    duplicate.refresh_from_db()
    legacy_module_binding.refresh_from_db()
    active_global = JenkinsJobBinding.objects.filter(
        environment__isnull=True,
        module__isnull=True,
        task_type=MetricRun.RunType.DAILY_FULL,
        is_active=True,
    )
    assert list(active_global.values_list("id", flat=True)) == [canonical.id]
    assert canonical.job_full_name == "AiApiTest-DWP-Daily-Full-Module"
    assert duplicate.is_active is False
    assert legacy_module_binding.is_active is True


def test_global_daily_binding_lock_uses_mysql_advisory_lock_and_releases_it():
    from metrics.management.commands.sync_jenkins_job_bindings import (
        GLOBAL_DAILY_BINDING_LOCK_NAME,
        GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS,
        global_daily_binding_lock,
    )

    with patch("metrics.management.commands.sync_jenkins_job_bindings.connection") as connection:
        connection.vendor = "mysql"
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)

        with global_daily_binding_lock():
            pass

    assert cursor.execute.call_args_list == [
        call(
            "SELECT GET_LOCK(%s, %s)",
            [GLOBAL_DAILY_BINDING_LOCK_NAME, GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS],
        ),
        call("SELECT RELEASE_LOCK(%s)", [GLOBAL_DAILY_BINDING_LOCK_NAME]),
    ]


def test_global_daily_binding_lock_rejects_mysql_lock_timeout():
    from metrics.management.commands.sync_jenkins_job_bindings import global_daily_binding_lock

    with patch("metrics.management.commands.sync_jenkins_job_bindings.connection") as connection:
        connection.vendor = "mysql"
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (0,)

        with pytest.raises(CommandError, match="global Daily"):
            with global_daily_binding_lock():
                pass

    cursor.execute.assert_called_once()


def test_global_daily_binding_lock_releases_mysql_advisory_lock_when_body_raises():
    from metrics.management.commands.sync_jenkins_job_bindings import (
        GLOBAL_DAILY_BINDING_LOCK_NAME,
        GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS,
        global_daily_binding_lock,
    )

    with patch("metrics.management.commands.sync_jenkins_job_bindings.connection") as connection:
        connection.vendor = "mysql"
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)

        with pytest.raises(RuntimeError, match="interrupted"):
            with global_daily_binding_lock():
                raise RuntimeError("interrupted")

    assert cursor.execute.call_args_list == [
        call(
            "SELECT GET_LOCK(%s, %s)",
            [GLOBAL_DAILY_BINDING_LOCK_NAME, GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS],
        ),
        call("SELECT RELEASE_LOCK(%s)", [GLOBAL_DAILY_BINDING_LOCK_NAME]),
    ]


def test_global_daily_binding_lock_keeps_sqlite_pytest_compatible():
    from metrics.management.commands.sync_jenkins_job_bindings import global_daily_binding_lock

    with patch("metrics.management.commands.sync_jenkins_job_bindings.connection") as connection:
        connection.vendor = "sqlite"

        with global_daily_binding_lock():
            pass

    connection.cursor.assert_not_called()


@pytest.mark.django_db
def test_sync_jenkins_job_bindings_ignores_retired_empty_job_name_overrides(monkeypatch):
    MetricEnvironment.objects.create(
        env_key="mock-gbif",
        env_name="模拟测试环境",
        base_url="https://api.gbif.org",
        is_active=True,
    )
    MetricModule.objects.create(
        package_name="Species",
        case_path="test_case/Species",
        module_name="物种查询",
        module_dev="张三",
        module_test="王五",
        is_active=True,
    )
    monkeypatch.setenv("JENKINS_FAILED_RERUN_JOB_NAME", "")
    monkeypatch.setenv("JENKINS_MODULE_RERUN_JOB_NAME", "AiApiTest-DWP-Module-Rerun")
    monkeypatch.setenv("JENKINS_DAILY_FULL_JOB_NAME", "")

    stdout = StringIO()
    call_command("sync_jenkins_job_bindings", stdout=stdout)

    assert JenkinsJobBinding.objects.filter(
        task_type=MetricRun.RunType.FAILED_RERUN,
        job_full_name="AiApiTest-DWP-Failed-Rerun",
    ).exists()
    assert JenkinsJobBinding.objects.filter(task_type=MetricRun.RunType.MODULE_RERUN).exists()
    assert JenkinsJobBinding.objects.filter(
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
    ).exists()
    assert "skipped=0" in stdout.getvalue()


def test_sync_jenkins_results_once_runs_one_cycle_and_reports_counts():
    stdout = StringIO()

    with patch("metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle") as run_cycle:
        run_cycle.return_value = {
            "active_processed": 2,
            "daily_discovered": 2,
            "synced": 4,
            "failed": 0,
            "skipped": 1,
        }
        call_command("sync_jenkins_results", once=True, stdout=stdout)

    run_cycle.assert_called_once_with()
    output = stdout.getvalue()
    assert "active_processed=2" in output
    assert "daily_discovered=2" in output
    assert "synced=4" in output


def test_sync_jenkins_results_watch_rejects_non_positive_interval():
    with pytest.raises(CommandError, match="interval"):
        call_command("sync_jenkins_results", watch=True, interval=0)


def test_sync_jenkins_results_rejects_interval_without_watch():
    with pytest.raises(CommandError, match="watch"):
        call_command("sync_jenkins_results", interval=5)


def test_sync_jenkins_results_ignores_retired_environment_interval(monkeypatch):
    monkeypatch.setenv("JENKINS_BUILD_POLL_INTERVAL_SECONDS", "invalid")
    stdout = StringIO()
    stderr = StringIO()
    stats = {
        "active_processed": 0,
        "daily_discovered": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
    }

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        side_effect=[stats, KeyboardInterrupt],
    ), patch("metrics.management.commands.sync_jenkins_results.time.sleep") as sleep:
        call_command("sync_jenkins_results", watch=True, stdout=stdout, stderr=stderr)

    sleep.assert_called_once_with(10)
    assert stderr.getvalue() == ""


def test_sync_jenkins_results_sigterm_stops_watch_cleanly():
    stdout = StringIO()
    stats = {
        "active_processed": 0,
        "daily_discovered": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
    }
    registered_handlers = {}

    def fake_signal(signum, handler):
        previous = registered_handlers.get(signum)
        registered_handlers[signum] = handler
        return previous

    def request_stop(_interval):
        registered_handlers[signal.SIGTERM](signal.SIGTERM, None)

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        return_value=stats,
    ) as run_cycle, patch(
        "metrics.management.commands.sync_jenkins_results.signal.getsignal",
        return_value=signal.SIG_DFL,
    ), patch(
        "metrics.management.commands.sync_jenkins_results.signal.signal",
        side_effect=fake_signal,
    ), patch(
        "metrics.management.commands.sync_jenkins_results.time.sleep",
        side_effect=request_stop,
    ):
        call_command("sync_jenkins_results", watch=True, interval=1, stdout=stdout)

    run_cycle.assert_called_once_with()
    assert "worker stopped" in stdout.getvalue()


def test_sync_jenkins_results_watch_repeats_until_interrupted():
    stdout = StringIO()
    stats = {
        "active_processed": 0,
        "daily_discovered": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
    }

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        side_effect=[stats, KeyboardInterrupt],
    ) as run_cycle, patch("metrics.management.commands.sync_jenkins_results.time.sleep") as sleep:
        call_command("sync_jenkins_results", watch=True, interval=1, stdout=stdout)

    assert run_cycle.call_count == 2
    sleep.assert_called_once_with(1)
    assert "worker stopped" in stdout.getvalue()


@pytest.mark.django_db
def test_seed_environment_is_idempotent_and_projects_the_image_catalog():
    call_command("seed_environment")
    call_command("seed_environment")

    assert MetricEnvironment.objects.count() == 1
    environment = MetricEnvironment.objects.get(env_key="gbif-public")
    assert environment.env_name == "GBIF Public API"
    assert environment.base_url == "https://api.gbif.org"
    assert environment.url_desc == "GBIF public API test environment"
    assert environment.is_active is True


@pytest.mark.django_db
def test_seed_demo_metrics_creates_readonly_snapshots_without_duplicates(tmp_path):
    case_root = tmp_path / "api-test" / "test_case"
    write_case_file(
        case_root / "test_gbif_case" / "test_actual_api.py",
        """
class TestActualAPI:
    def test_search_species(self):
        pass

    def test_deliberate_assertion_failure(self):
        pass
""",
    )
    write_case_file(
        case_root / "test_gbif_case_module2" / "test_module2_api.py",
        """
import pytest

def test_species_name():
    pass

@pytest.mark.skipif(True, reason="固定跳过用例！")
def test_species_occurrence_datasets():
    pass
""",
    )
    yaml_path = tmp_path / "package_module.yaml"
    write_module_yaml(
        yaml_path,
        """
test_gbif_case:
  module_name: 示例模块1
  module_dev: 张三
  module_test: 王五
test_gbif_case_module2:
  module_name: 示例模块2
  module_dev: 赵四
  module_test: 王麻子
""",
    )
    environment_yaml_path = tmp_path / "api-test" / "utils" / "package_environment.yaml"
    environment_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    environment_yaml_path.write_text(
        """gbif-public:
  base_url: https://api.gbif.org
  url_name: GBIF Public API
  url_desc: GBIF public API test environment
""",
        encoding="utf-8",
    )
    with override_settings(REPO_ROOT=tmp_path):
        call_command("sync_modules", source=str(yaml_path))
        call_command("seed_environment")

        stdout = StringIO()
        call_command("seed_demo_metrics", stdout=stdout)
        old_module = MetricModule.objects.get(package_name="test_gbif_case")
        old_snapshot = ModuleSnapshot.objects.get(environment__env_key="gbif-public", module=old_module)
        metric_model("TestCaseResult").objects.create(
            environment=old_snapshot.environment,
            module=old_module,
            module_snapshot=old_snapshot,
            node_id="test_case/test_gbif_case/test_demo.py::test_search_species",
            case_name="test_search_species",
            case_summary="旧版假用例残留",
            display_status="failed",
            execution_status="failed",
            is_current=True,
        )
        call_command("seed_demo_metrics", stdout=stdout)

    environment = MetricEnvironment.objects.get(env_key="gbif-public")
    assert MetricRun.objects.count() == 1
    assert EnvironmentSnapshot.objects.filter(environment=environment).count() == 1
    assert ModuleSnapshot.objects.filter(environment=environment).count() == 2
    case_results = metric_model("TestCaseResult").objects.filter(environment=environment, is_current=True)
    trend_rows = metric_model("ModuleRunHistory").objects.filter(environment=environment)
    assert case_results.count() == 4
    assert case_results.values("environment_id", "module_id", "node_id", "is_current").distinct().count() == 4
    assert set(case_results.values_list("node_id", flat=True)) == {
        "test_case/test_gbif_case/test_actual_api.py::TestActualAPI::test_search_species",
        "test_case/test_gbif_case/test_actual_api.py::TestActualAPI::test_deliberate_assertion_failure",
        "test_case/test_gbif_case_module2/test_module2_api.py::test_species_name",
        "test_case/test_gbif_case_module2/test_module2_api.py::test_species_occurrence_datasets",
    }
    assert not case_results.filter(node_id__contains="test_demo.py").exists()
    assert metric_model("TestCaseResult").objects.filter(node_id__contains="test_demo.py", is_current=False).exists()
    assert case_results.filter(display_status="failed").count() == 1
    assert case_results.filter(display_status="skipped").count() == 1
    assert trend_rows.count() == 60
    assert trend_rows.values("environment_id", "module_id", "run_date", "run_type", "source_run_id").distinct().count() == 60
    snapshot = EnvironmentSnapshot.objects.get(environment=environment)
    assert snapshot.total_count == 4
    assert snapshot.failed_count == 1
    assert snapshot.skipped_count == 1
    assert str(snapshot.pass_rate) == "0.750000"
    assert "dev-only" in stdout.getvalue()
    assert "case_results" in stdout.getvalue()
    assert "module_run_history" in stdout.getvalue()
