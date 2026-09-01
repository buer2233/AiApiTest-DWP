"""MCP callers 与 test_methods 的覆盖关系分析。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_TEST_NAME_RE = re.compile(r"\b(test_[A-Za-z0-9_]+)\b")


def _caller_test_names(output: str) -> list[str]:
    """优先读取 MCP JSON，旧版文本输出再降级正则提取。"""
    try:
        payload = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("callers"), list):
        return sorted(
            {
                str(item.get("name"))
                for item in payload["callers"]
                if isinstance(item, dict) and str(item.get("name") or "").startswith("test_")
            }
        )
    return sorted(set(_TEST_NAME_RE.findall(output or "")))


def select_consistency_symbols(
    facts: dict[str, Any],
    wrappers: list[dict[str, Any]],
    marked_tests: list[dict[str, Any]],
) -> tuple[list[str], str]:
    """选择可在 api-test-E9 图中反查的符号，并说明选择依据。"""
    wrapper_methods = {
        str(wrapper.get("method") or "")
        for wrapper in wrappers
        if str(wrapper.get("method") or "")
    }
    changed_symbols = [
        str(item.get("name") or "")
        for item in facts.get("symbols") or []
        if str(item.get("name") or "") in wrapper_methods
    ]
    if changed_symbols:
        return sorted(set(changed_symbols)), "changed_wrapper_symbol"

    endpoint_pairs = {
        (
            str(item.get("url") or ""),
            str(item.get("method") or item.get("http_method") or "").upper(),
        )
        for item in facts.get("endpoints") or []
    }
    endpoint_methods = [
        str(wrapper.get("method") or "")
        for wrapper in wrappers
        if (
            str(wrapper.get("url") or ""),
            str(wrapper.get("http_method") or "").upper(),
        )
        in endpoint_pairs
        and str(wrapper.get("method") or "")
    ]
    if endpoint_methods:
        return sorted(set(endpoint_methods)), "changed_endpoint_wrapper"

    fallback_calls = [
        str(call)
        for test in marked_tests
        for call in test.get("calls") or []
        if str(call) in wrapper_methods
    ]
    if fallback_calls:
        return sorted(set(fallback_calls)), "marked_test_wrapper_calls"
    return [], "no_graph_mappable_symbol"


def callers_coverage(
    graph: Any,
    project_path: str | Path,
    symbols: list[dict[str, str]],
    test_methods: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """反查每个变更符号的测试调用方并标出未覆盖符号。"""
    known_tests = {str(item.get("test_name") or item.get("name") or "") for item in test_methods}
    rows: list[dict[str, Any]] = []
    for symbol_item in symbols:
        symbol = str(symbol_item.get("name") or "")
        if not symbol:
            continue
        try:
            output = graph.callers(project_path, symbol)
            caller_names = _caller_test_names(output or "")
            covered = [name for name in caller_names if name in known_tests]
            rows.append({"symbol": symbol, "callers": caller_names, "covered_tests": covered, "has_coverage": bool(covered), "error": ""})
        except Exception as exc:  # noqa: BLE001
            rows.append({"symbol": symbol, "callers": [], "covered_tests": [], "has_coverage": False, "error": str(exc)})
    return rows


def check_consistency(marked_tests: list[str], caller_tests: list[str]) -> dict[str, Any]:
    """比较 revision mark 关联用例和 callers 反查用例，并说明差异。"""
    marked = set(marked_tests)
    callers = set(caller_tests)
    return {
        "marked_tests": sorted(marked),
        "caller_tests": sorted(callers),
        "only_marked": sorted(marked - callers),
        "only_callers": sorted(callers - marked),
        "consistent": marked == callers,
        "explanation": "两路结果一致" if marked == callers else "可能存在漏打 mark 或 MCP callers 解析差异，需人工复核",
    }
