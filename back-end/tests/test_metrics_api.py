from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from metrics.models import (
    EnvironmentSnapshot,
    ModuleSnapshot,
    TestEnvironment as MetricEnvironment,
    TestModule as MetricModule,
    TestRun as MetricRun,
)


pytestmark = pytest.mark.api


@pytest.fixture
def environment(db) -> MetricEnvironment:
    return MetricEnvironment.objects.create(
        env_key="mock-gbif",
        env_name="模拟测试环境",
        base_url="https://api.gbif.org",
        is_active=True,
    )


@pytest.fixture
def modules(db) -> list[MetricModule]:
    return [
        MetricModule.objects.create(
            package_name="test_gbif_case",
            case_path="test_case/test_gbif_case",
            module_name="示例模块1",
            module_dev="张三",
            module_test="王五",
        ),
        MetricModule.objects.create(
            package_name="test_gbif_case_module2",
            case_path="test_case/test_gbif_case_module2",
            module_name="示例模块2",
            module_dev="赵四",
            module_test="王麻子",
        ),
    ]


@pytest.fixture
def seeded_snapshots(environment: MetricEnvironment, modules: list[MetricModule]):
    started_at = timezone.datetime(2026, 7, 4, 9, 0, tzinfo=timezone.get_current_timezone())
    finished_at = timezone.datetime(2026, 7, 4, 9, 18, 24, tzinfo=timezone.get_current_timezone())
    run = MetricRun.objects.create(
        run_key="demo-daily-full",
        run_type=MetricRun.RunType.DAILY_FULL,
        environment=environment,
        status=MetricRun.Status.SUCCESS,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=Decimal("1104.00"),
        summary_json={"source": "test"},
    )
    EnvironmentSnapshot.objects.create(
        environment=environment,
        latest_run=run,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=Decimal("1104.00"),
        total_count=200,
        failed_count=8,
        passed_count=189,
        skipped_count=3,
        pass_rate=Decimal("0.960000"),
    )
    ModuleSnapshot.objects.create(
        environment=environment,
        module=modules[0],
        latest_run=run,
        completed_at=finished_at,
        duration_seconds=Decimal("552.00"),
        total_count=100,
        failed_count=4,
        passed_count=93,
        skipped_count=3,
        pass_rate=Decimal("0.960000"),
    )
    ModuleSnapshot.objects.create(
        environment=environment,
        module=modules[1],
        latest_run=run,
        completed_at=finished_at,
        duration_seconds=Decimal("552.00"),
        total_count=100,
        failed_count=4,
        passed_count=96,
        skipped_count=0,
        pass_rate=Decimal("0.960000"),
    )
    return run


def test_environment_list_is_login_readable_for_admin_and_member(admin_client, member_client, environment):
    for client in [admin_client, member_client]:
        response = client.get("/api/v1/test-environments")

        assert response.status_code == 200
        assert response.data["data"] == [
            {
                "id": environment.id,
                "env_key": "mock-gbif",
                "env_name": "模拟测试环境",
                "base_url": "https://api.gbif.org",
            }
        ]


def test_environment_summary_returns_snapshot_fields(admin_client, environment, seeded_snapshots):
    response = admin_client.get(f"/api/v1/test-environments/{environment.id}/summary")

    assert response.status_code == 200
    data = response.data["data"]
    assert data["environment"]["env_name"] == "模拟测试环境"
    assert data["environment"]["base_url"] == "https://api.gbif.org"
    assert data["total_count"] == 200
    assert data["failed_count"] == 8
    assert data["passed_count"] == 189
    assert data["skipped_count"] == 3
    assert data["pass_rate"] == "0.960000"
    assert data["duration_seconds"] == "1104.00"
    assert data["actions"] == {"generate_report": True}


def test_environment_summary_without_snapshot_returns_empty_statistics(admin_client, environment):
    response = admin_client.get(f"/api/v1/test-environments/{environment.id}/summary")

    assert response.status_code == 200
    data = response.data["data"]
    assert data["environment"]["env_name"] == "模拟测试环境"
    assert data["started_at"] is None
    assert data["finished_at"] is None
    assert data["duration_seconds"] is None
    assert data["total_count"] == 0
    assert data["failed_count"] == 0
    assert data["passed_count"] == 0
    assert data["skipped_count"] == 0
    assert data["pass_rate"] == "0.000000"


def test_environment_summary_unknown_id_returns_404(admin_client):
    response = admin_client.get("/api/v1/test-environments/999999/summary")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "environment_not_found"


def test_metrics_api_requires_login(api_client, environment):
    urls = [
        "/api/v1/test-environments",
        f"/api/v1/test-environments/{environment.id}/summary",
        f"/api/v1/module-snapshots?environment_id={environment.id}",
    ]

    for url in urls:
        response = api_client.get(url)
        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_required"


def test_module_snapshots_return_core_fields_actions_and_pagination(admin_client, environment, seeded_snapshots):
    response = admin_client.get(
        "/api/v1/module-snapshots",
        {"environment_id": environment.id, "page": 1, "per_page": 20},
    )

    assert response.status_code == 200
    assert response.data["meta"] == {"total": 2, "page": 1, "per_page": 20, "total_pages": 1}
    row = response.data["data"][0]
    assert row["package_name"] in {"test_gbif_case", "test_gbif_case_module2"}
    assert row["module_name"].startswith("示例模块")
    assert row["module_dev"] in {"张三", "赵四"}
    assert row["module_test"] in {"王五", "王麻子"}
    assert row["total_count"] == 100
    assert row["failed_count"] == 4
    assert row["skipped_count"] in {0, 3}
    assert row["pass_rate"] == "0.960000"
    assert row["duration_seconds"] == "552.00"
    assert row["actions"] == {
        "failed_rerun": False,
        "module_rerun": False,
        "trend_7d": True,
        "trend_30d": True,
        "jenkins_tasks": False,
    }


@pytest.mark.parametrize(
    "params,expected_total",
    [
        ({"module_name": "模块1"}, 1),
        ({"package_name": "module2"}, 1),
        ({"module_test": "王五"}, 1),
        ({"pass_rate_lte": "96"}, 2),
    ],
)
def test_module_snapshots_filter_by_module_fields_and_pass_rate(
    admin_client,
    environment,
    seeded_snapshots,
    params,
    expected_total,
):
    response = admin_client.get("/api/v1/module-snapshots", {"environment_id": environment.id, **params})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == expected_total


def test_module_snapshots_accept_comma_separated_sort_fields(admin_client, environment, modules):
    older = timezone.datetime(2026, 7, 4, 9, 0, tzinfo=timezone.get_current_timezone())
    newer = timezone.datetime(2026, 7, 4, 10, 0, tzinfo=timezone.get_current_timezone())
    third_module = MetricModule.objects.create(
        package_name="test_gbif_case_module3",
        case_path="test_case/test_gbif_case_module3",
        module_name="示例模块3",
        module_dev="李四",
        module_test="赵六",
    )
    low_old = ModuleSnapshot.objects.create(
        environment=environment,
        module=modules[0],
        completed_at=older,
        total_count=100,
        failed_count=10,
        passed_count=90,
        pass_rate=Decimal("0.900000"),
    )
    low_new = ModuleSnapshot.objects.create(
        environment=environment,
        module=modules[1],
        completed_at=newer,
        total_count=100,
        failed_count=10,
        passed_count=90,
        pass_rate=Decimal("0.900000"),
    )
    high = ModuleSnapshot.objects.create(
        environment=environment,
        module=third_module,
        completed_at=newer,
        total_count=100,
        failed_count=4,
        passed_count=96,
        pass_rate=Decimal("0.960000"),
    )

    response = admin_client.get(
        "/api/v1/module-snapshots",
        {"environment_id": environment.id, "sort": "pass_rate,-completed_at"},
    )

    assert response.status_code == 200
    assert [row["id"] for row in response.data["data"]] == [low_new.id, low_old.id, high.id]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"environment_id": "999999"},
        {"environment_id": "abc"},
        {"environment_id": "1", "page": "0"},
        {"environment_id": "1", "per_page": "101"},
        {"environment_id": "1", "pass_rate_lte": "101"},
        {"environment_id": "1", "sort": "drop_table"},
    ],
)
def test_module_snapshots_reject_invalid_query_params(admin_client, environment, params):
    response = admin_client.get("/api/v1/module-snapshots", params)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_module_snapshots_zero_total_count_does_not_break_response(admin_client, environment, modules):
    ModuleSnapshot.objects.create(
        environment=environment,
        module=modules[0],
        total_count=0,
        failed_count=0,
        passed_count=0,
        skipped_count=0,
        pass_rate=Decimal("0.000000"),
    )

    response = admin_client.get("/api/v1/module-snapshots", {"environment_id": environment.id})

    assert response.status_code == 200
    assert response.data["data"][0]["pass_rate"] == "0.000000"
