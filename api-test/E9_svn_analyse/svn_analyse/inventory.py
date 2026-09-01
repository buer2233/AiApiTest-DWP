# -*- coding: utf-8 -*-
"""扫描 api-test-E9 中已实现的接口 URL、封装方法和用例。"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

from svn_analyse import paths
from svn_analyse.revision import revision_mark

paths.ensure_framework_importable()

_MARK_RE = re.compile(r"pytest\.mark\.(r\d+)")
_CALL_RE = re.compile(r"\.([A-Za-z_]\w*)\s*\(")


def index_db_path(api_test_root: str | Path) -> Path:
    """返回 api-test-E9 的 URL 索引 SQLite 路径。"""
    root = Path(api_test_root)
    return root / "tools" / "page_api_index.sqlite3"


def scan_wrappers(
    api_test_root: str | Path, *, refresh_index: bool = False
) -> list[dict[str, Any]]:
    """调用 E9 扫描器更新 SQLite，并从库中构建封装库存快照。"""
    root = Path(api_test_root).resolve()
    if not (root / "page_api").is_dir():
        return []
    scanner = _load_scan_page_api(root)
    scanner.update_index(root / "page_api", index_db_path(root), refresh=refresh_index)
    from skill_utils.api_index_db import load_methods

    wrappers: list[dict[str, Any]] = []
    for item in load_methods(index_db_path(root)):
        class_name = str(item["class_name"])
        method = str(item["api_name"])
        wrappers.append(
            {
                "url": item["api_url"],
                "http_method": item["http_method"],
                "class": class_name,
                "method": method,
                "wrapper": f"{class_name}.{method}" if class_name else method,
                "file": item["file"],
                "line": item["line"],
            }
        )
    return wrappers


def scan_tests(api_test_root: str | Path) -> list[dict[str, Any]]:
    """扫描 test_case 中的测试方法及 revision mark。"""
    root = Path(api_test_root)
    case_root = root / "test_case"
    tests: list[dict[str, Any]] = []
    if not case_root.is_dir():
        return tests
    for py_file in sorted(case_root.rglob("test_*.py")):
        text = _read(py_file)
        file_marks = _MARK_RE.findall(text)
        rel = _rel(root, py_file)
        file_tests: list[dict[str, Any]] = []
        pending_marks: list[str] = []
        for line in text.splitlines():
            mark_on_line = _MARK_RE.findall(line)
            if mark_on_line:
                pending_marks.extend(mark_on_line)
            test_match = re.match(r"^    def (test_\w+)\s*\(", line)
            if test_match:
                marks = list(dict.fromkeys(pending_marks or file_marks))
                file_tests.append(
                    {
                        "name": test_match.group(1),
                        "file": rel,
                        "marks": marks,
                    }
                )
                pending_marks = []
        _attach_calls(text, file_tests)
        tests.extend(file_tests)
    return tests


def _attach_calls(text: str, file_tests: list[dict[str, Any]]) -> None:
    """把每个 test_ 方法体里的 .method( 调用挂到对应用例。"""
    if not file_tests:
        return
    parts = re.split(r"(?m)^    def (test_\w+)\s*\(", text)
    # 拆分结果：前导文本、方法名和方法体交替出现。
    bodies: dict[str, str] = {}
    index = 1
    while index + 1 < len(parts):
        bodies[parts[index]] = parts[index + 1]
        index += 2
    for item in file_tests:
        body = bodies.get(item["name"], "")
        item["calls"] = list(dict.fromkeys(_CALL_RE.findall(body)))


def match_existing(
    endpoints: list[dict[str, Any]],
    inventory: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """按 SQLite URL/HTTP 等值查询变更接口的已有封装和关联用例。"""
    wrappers = inventory.get("wrappers") or []
    tests = inventory.get("tests") or []
    by_url_method: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for wrapper in wrappers:
        key = (str(wrapper.get("url") or ""), str(wrapper.get("http_method") or "").upper())
        by_url_method.setdefault(key, []).append(wrapper)

    matched: list[dict[str, Any]] = []
    sql_matches = None
    if db_path is not None:
        api_test_root = Path(db_path).resolve().parents[1]
        if not (api_test_root / "skill_utils").is_dir():
            api_test_root = paths.FRAMEWORK_ROOT
        if str(api_test_root) not in sys.path:
            sys.path.insert(0, str(api_test_root))
        from skill_utils.api_index_db import find_methods_by_endpoint

        sql_matches = find_methods_by_endpoint
    for endpoint in endpoints:
        url = endpoint.get("url") or ""
        http_method = (endpoint.get("method") or endpoint.get("http_method") or "").upper()
        if sql_matches is not None:
            hits = [
                {
                    "url": url,
                    "http_method": item["http_method"],
                    "class": item["class_name"],
                    "method": item["api_name"],
                    "wrapper": (
                        f"{item['class_name']}.{item['api_name']}"
                        if item["class_name"]
                        else item["api_name"]
                    ),
                    "file": item["file"],
                    "line": item["line"],
                }
                for item in sql_matches(Path(db_path), url, http_method)
            ]
        else:
            hits = by_url_method.get((url, http_method), []) + by_url_method.get((url, ""), [])
        related_tests: list[str] = []
        wrapper_names = {item.get("method") for item in hits}
        for test in tests:
            if wrapper_names & set(test.get("calls") or []):
                related_tests.append(test["name"])
        if hits:
            for wrapper in hits:
                matched.append(
                    {
                        "url": url,
                        "http_method": http_method,
                        "wrapper": wrapper.get("wrapper") or wrapper.get("method"),
                        "file": wrapper.get("file"),
                        "line": wrapper.get("line"),
                        "has_wrapper": True,
                        "tests": related_tests,
                    }
                )
        else:
            matched.append(
                {
                    "url": url,
                    "http_method": http_method,
                    "wrapper": "",
                    "file": "",
                    "line": 0,
                    "has_wrapper": False,
                    "tests": [],
                }
            )
    return matched


def build_inventory(
    api_test_root: str | Path, *, refresh_index: bool = False
) -> dict[str, Any]:
    """更新 URL 索引后构建不含敏感数据的接口和用例快照。"""
    wrappers = scan_wrappers(api_test_root, refresh_index=refresh_index)
    root = Path(api_test_root).resolve()
    from svn_analyse.test_methods import collect_test_methods
    from skill_utils.api_index_db import replace_test_methods, load_test_methods

    test_records = collect_test_methods(root / "test_case")
    replace_test_methods(index_db_path(root), test_records)
    tests = [
        {
            "name": item["test_name"],
            "file": item["file"],
            "marks": [mark for mark in str(item["marks"]).split(";") if mark],
            "title": item["title"],
            "calls": [call for call in str(item["calls"]).split(";") if call],
            "line": item["line"],
        }
        for item in load_test_methods(index_db_path(root))
    ]
    return {
        "api_test_root": str(Path(api_test_root)),
        "wrappers": wrappers,
        "tests": tests,
        "urls": sorted({item["url"] for item in wrappers}),
    }


def write_inventory(
    api_test_root: str | Path, dest: str | Path, *, refresh_index: bool = False
) -> dict[str, Any]:
    """写入接口库存 JSON 快照，SQLite 保持为判定数据源。"""
    inventory = build_inventory(api_test_root, refresh_index=refresh_index)
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return inventory


def tests_for_revision(inventory: dict[str, Any], revision: int) -> list[dict[str, Any]]:
    mark = revision_mark(revision)
    return [item for item in inventory.get("tests", []) if mark in (item.get("marks") or [])]


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _load_scan_page_api(api_test_root: Path):
    """按 api-test-E9 根目录加载扫描器，避免根仓库与独立仓库导入冲突。"""
    framework_root = api_test_root
    if not (framework_root / "tools" / "scan_page_api.py").is_file():
        framework_root = paths.FRAMEWORK_ROOT
    project_key = str(framework_root)
    module_name = "_e9_scan_page_api_" + str(abs(hash(project_key)))
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    if project_key not in sys.path:
        sys.path.insert(0, project_key)
    module_path = framework_root / "tools" / "scan_page_api.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 E9 page_api 扫描器：{module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
