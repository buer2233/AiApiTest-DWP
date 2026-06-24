"""Allure 结果解析测试。
本文件验证后端能从 Allure 原始 JSON 中提取失败用例，并能安全处理缺失目录。
"""

import json
from pathlib import Path

from apps.test_runs.services.allure_results_parser import parse_allure_failures


def write_result(results_dir: Path, filename: str, payload: dict):
    """写入一份测试用 Allure result JSON。
    Args:
        results_dir: 临时 Allure 结果目录。
        filename: 结果文件名。
        payload: 写入文件的 JSON 内容。
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / filename).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_parse_allure_failures_extracts_failed_case_details(tmp_path):
    """验证解析器只提取失败用例并转换为 FailureCase 所需字段。"""
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
    """验证 Allure 结果目录不存在时返回空列表而不是抛异常。"""
    failures = parse_allure_failures(tmp_path / "missing-results")

    assert failures == []
