import json
from pathlib import Path

from apps.test_runs.services.allure_results_parser import parse_allure_failures


def write_result(results_dir: Path, filename: str, payload: dict):
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / filename).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_parse_allure_failures_extracts_failed_case_details(tmp_path):
    results_dir = tmp_path / "allure-results"
    write_result(
        results_dir,
        "failed-result.json",
        {
            "uuid": "case-1",
            "name": "test species search",
            "fullName": "test_case.test_gbif_case.test_gbif_api#test_species_search",
            "description": "Search species by keyword",
            "status": "failed",
            "statusDetails": {
                "message": "AssertionError: expected 200",
                "trace": "AssertionError: expected 200\nresponse code was 500",
            },
            "labels": [
                {"name": "suite", "value": "test_case.test_gbif_case"},
                {"name": "package", "value": "test_case.test_gbif_case"},
            ],
        },
    )
    write_result(
        results_dir,
        "passed-result.json",
        {
            "uuid": "case-2",
            "name": "test ignored passed",
            "fullName": "test_case.test_gbif_case.test_ok#test_ok",
            "status": "passed",
        },
    )

    failures = parse_allure_failures(results_dir)

    assert len(failures) == 1
    assert failures[0] == {
        "node_id": "test_case/test_gbif_case/test_gbif_api.py::test_species_search",
        "case_name": "test species search",
        "module_path": "test_case/test_gbif_case",
        "description": "Search species by keyword",
        "error_type": "AssertionError",
        "assertion_message": "AssertionError: expected 200",
        "status": "failed",
    }


def test_parse_allure_failures_returns_empty_list_for_missing_directory(tmp_path):
    failures = parse_allure_failures(tmp_path / "missing-results")

    assert failures == []
