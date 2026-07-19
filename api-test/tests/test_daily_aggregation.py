import json

import pytest

from tools.daily_aggregation import (
    DailyAggregationError,
    DailyWorkerArtifact,
    aggregate_daily_run,
    load_module_keys,
)


def _write_module_manifest(path, module_keys):
    path.write_text(
        "\n".join(f"{module_key}:\n  module_name: {module_key}" for module_key in module_keys) + "\n",
        encoding="utf-8",
    )


def _write_worker_artifact(
    tmp_path,
    module_key,
    *,
    status,
    counts,
    failed_nodeids=None,
    run_suffix="",
    summary_overrides=None,
):
    run_dir = tmp_path / f"worker-{module_key}{run_suffix}"
    allure_results_dir = run_dir / "allure-results"
    allure_results_dir.mkdir(parents=True)
    (allure_results_dir / "result.json").write_text(
        json.dumps({"module_key": module_key}, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = {
        "status": status,
        "return_code": 0 if status == "passed" else 1,
        "failed_nodeids": failed_nodeids or [],
        "allure_results_dir": str(allure_results_dir),
        "allure_report_dir": str(run_dir / "allure-report"),
        "allure_report_status": "generated",
        "allure_report_message": "generated",
        **counts,
    }
    summary.update(summary_overrides or {})
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return DailyWorkerArtifact(module_key=module_key, run_dir=run_dir)


def test_aggregate_daily_run_collects_all_worker_results_after_test_failure(tmp_path):
    module_manifest = tmp_path / "package_module.yaml"
    _write_module_manifest(module_manifest, ["module-beta", "module-alpha"])
    alpha = _write_worker_artifact(
        tmp_path,
        "module-alpha",
        status="passed",
        counts={
            "total_count": 2,
            "passed_count": 2,
            "failed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
        },
    )
    beta = _write_worker_artifact(
        tmp_path,
        "module-beta",
        status="failed",
        counts={
            "total_count": 3,
            "passed_count": 1,
            "failed_count": 1,
            "error_count": 1,
            "skipped_count": 1,
        },
        failed_nodeids=["test_case/test_beta.py::test_failed"],
    )
    gamma = _write_worker_artifact(
        tmp_path,
        "module-gamma",
        status="passed",
        counts={
            "total_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
        },
    )
    parent_run_dir = tmp_path / "daily-parent"

    _write_module_manifest(module_manifest, ["module-beta", "module-alpha", "module-gamma"])

    summary = aggregate_daily_run(module_manifest, [beta, alpha, gamma], parent_run_dir)

    assert summary["status"] == "failed"
    assert summary["module_count"] == 3
    assert summary["total_count"] == 6
    assert summary["passed_count"] == 4
    assert summary["failed_count"] == 1
    assert summary["error_count"] == 1
    assert summary["skipped_count"] == 1
    assert summary["failed_nodeids"] == ["test_case/test_beta.py::test_failed"]
    assert summary["allure_results_dir"] == "allure-results"
    assert [detail["module_key"] for detail in summary["modules"]] == [
        "module-alpha",
        "module-beta",
        "module-gamma",
    ]
    assert (parent_run_dir / "summary.json").is_file()
    assert (parent_run_dir / "module-details" / "module-alpha.json").is_file()
    assert (parent_run_dir / "module-details" / "module-beta.json").is_file()
    assert (parent_run_dir / "module-details" / "module-gamma.json").is_file()
    assert (parent_run_dir / "allure-results" / "module-alpha" / "result.json").is_file()
    assert (parent_run_dir / "allure-results" / "module-beta" / "result.json").is_file()
    assert (parent_run_dir / "allure-results" / "module-gamma" / "result.json").is_file()


@pytest.mark.parametrize(
    ("manifest_content", "expected_code"),
    [
        ("", "empty_module_manifest"),
        (
            """
module-alpha:
  module_name: Alpha
module-alpha:
  module_name: Duplicate Alpha
""".lstrip(),
            "duplicate_module_key",
        ),
        (
            """
../escape:
  module_name: Escape
""".lstrip(),
            "invalid_module_key",
        ),
        (
            """
'..\\escape':
  module_name: Escape
""".lstrip(),
            "invalid_module_key",
        ),
    ],
)
def test_load_module_keys_rejects_empty_duplicate_or_unsafe_module_manifest(
    tmp_path, manifest_content, expected_code
):
    module_manifest = tmp_path / "package_module.yaml"
    module_manifest.write_text(manifest_content, encoding="utf-8")

    with pytest.raises(DailyAggregationError) as exc_info:
        load_module_keys(module_manifest)

    assert exc_info.value.diagnostic["code"] == expected_code


@pytest.mark.parametrize(
    ("artifact_keys", "expected_code"),
    [
        (["module-alpha"], "missing_module_details"),
        (["module-alpha", "module-alpha", "module-beta"], "duplicate_module_detail"),
        (["module-alpha", "module-beta", "module-unknown"], "unknown_module_detail"),
    ],
)
def test_aggregate_daily_run_rejects_incomplete_or_invalid_module_details(
    tmp_path, artifact_keys, expected_code
):
    module_manifest = tmp_path / "package_module.yaml"
    _write_module_manifest(module_manifest, ["module-alpha", "module-beta"])
    artifacts = [
        _write_worker_artifact(
            tmp_path,
            module_key,
            status="passed",
            counts={
                "total_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "error_count": 0,
                "skipped_count": 0,
            },
            run_suffix=f"-{index}",
        )
        for index, module_key in enumerate(artifact_keys)
    ]
    parent_run_dir = tmp_path / "daily-parent-invalid"

    with pytest.raises(DailyAggregationError) as exc_info:
        aggregate_daily_run(module_manifest, artifacts, parent_run_dir)

    assert exc_info.value.diagnostic["code"] == expected_code
    assert not (parent_run_dir / "summary.json").exists()


def test_aggregate_daily_run_rejects_missing_worker_summary_without_partial_output(tmp_path):
    module_manifest = tmp_path / "package_module.yaml"
    _write_module_manifest(module_manifest, ["module-alpha"])
    missing_artifact = DailyWorkerArtifact(
        module_key="module-alpha",
        run_dir=tmp_path / "missing-worker-run",
    )
    parent_run_dir = tmp_path / "daily-parent-missing-summary"

    with pytest.raises(DailyAggregationError) as exc_info:
        aggregate_daily_run(module_manifest, [missing_artifact], parent_run_dir)

    assert exc_info.value.diagnostic["code"] == "missing_worker_summary"
    assert not (parent_run_dir / "summary.json").exists()


def test_aggregate_daily_run_preserves_existing_parent_allure_archive(tmp_path):
    module_manifest = tmp_path / "package_module.yaml"
    _write_module_manifest(module_manifest, ["module-alpha"])
    artifact = _write_worker_artifact(
        tmp_path,
        "module-alpha",
        status="passed",
        counts={
            "total_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
        },
    )
    parent_run_dir = tmp_path / "daily-parent-existing"
    existing_result = parent_run_dir / "allure-results" / "module-alpha" / "previous.json"
    existing_result.parent.mkdir(parents=True)
    existing_result.write_text("preserve", encoding="utf-8")

    with pytest.raises(DailyAggregationError) as exc_info:
        aggregate_daily_run(module_manifest, [artifact], parent_run_dir)

    assert exc_info.value.diagnostic["code"] == "existing_parent_artifact"
    assert existing_result.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize(
    "summary_overrides",
    [
        {"status": "unknown"},
        {"status": 1},
        {"return_code": "1"},
        {"return_code": True},
        {"failed_nodeids": ["test_case/test_alpha.py::test_failure", 1]},
        {"status": "passed", "return_code": 1},
        {"status": "failed", "return_code": 0},
        {"total_count": True},
        {"failed_count": True},
        {"passed_count": True},
        {"skipped_count": True},
        {"error_count": True},
        {"failed_nodeids": ["test_case/test_alpha.py::test_failure"]},
        {"status": "failed", "return_code": 1, "failed_nodeids": [""]},
        {
            "status": "failed",
            "return_code": 1,
            "failed_nodeids": ["  test_case/test_alpha.py::test_failure  "],
        },
        {
            "status": "failed",
            "return_code": 1,
            "failed_nodeids": [
                "test_case/test_alpha.py::test_failure",
                "test_case/test_alpha.py::test_failure",
            ],
        },
    ],
)
def test_aggregate_daily_run_rejects_invalid_worker_summary_contract(tmp_path, summary_overrides):
    module_manifest = tmp_path / "package_module.yaml"
    _write_module_manifest(module_manifest, ["module-alpha"])
    artifact = _write_worker_artifact(
        tmp_path,
        "module-alpha",
        status="passed",
        counts={
            "total_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
        },
        summary_overrides=summary_overrides,
    )
    parent_run_dir = tmp_path / "daily-parent-invalid-summary"

    with pytest.raises(DailyAggregationError) as exc_info:
        aggregate_daily_run(module_manifest, [artifact], parent_run_dir)

    assert exc_info.value.diagnostic["code"] == "invalid_worker_summary"
    assert not (parent_run_dir / "summary.json").exists()
