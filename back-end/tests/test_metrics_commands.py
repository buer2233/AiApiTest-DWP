from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from metrics.models import (
    EnvironmentSnapshot,
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
def test_seed_environment_is_idempotent_and_updates_public_configuration():
    call_command("seed_environment")
    call_command("seed_environment")

    assert MetricEnvironment.objects.count() == 1
    environment = MetricEnvironment.objects.get(env_key="mock-gbif")
    assert environment.env_name == "模拟测试环境"
    assert environment.base_url == "https://api.gbif.org"
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
    with override_settings(REPO_ROOT=tmp_path):
        call_command("sync_modules", source=str(yaml_path))
        call_command("seed_environment")

        stdout = StringIO()
        call_command("seed_demo_metrics", stdout=stdout)
        old_module = MetricModule.objects.get(package_name="test_gbif_case")
        old_snapshot = ModuleSnapshot.objects.get(environment__env_key="mock-gbif", module=old_module)
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

    environment = MetricEnvironment.objects.get(env_key="mock-gbif")
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
