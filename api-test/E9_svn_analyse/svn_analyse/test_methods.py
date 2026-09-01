"""扫描 pytest 用例并提取 test_methods 关联元数据。"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


_MARK_RE = re.compile(r"pytest\.mark\.(r\d+)")
_CALL_RE = re.compile(r"\.([A-Za-z_]\w*)\s*\(")


def _decorator_marks(decorators: list[ast.expr]) -> list[str]:
    """从装饰器源码中提取 revision marks。"""
    marks: list[str] = []
    for decorator in decorators:
        try:
            text = ast.unparse(decorator)
        except AttributeError:
            text = ""
        marks.extend(_MARK_RE.findall(text))
    return list(dict.fromkeys(marks))


def _title(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """取测试方法 docstring 第一条非空行。"""
    for line in (ast.get_docstring(node, clean=True) or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _record_file(path: Path, root: Path, tree: ast.Module) -> list[dict[str, Any]]:
    """提取一个测试文件中模块级和类级测试方法。"""
    result: list[dict[str, Any]] = []
    file_marks: list[str] = []
    source = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()

    def add_method(node: ast.FunctionDef | ast.AsyncFunctionDef, inherited: list[str], owner: str) -> None:
        if not node.name.startswith("test_"):
            return
        marks = list(dict.fromkeys(inherited + _decorator_marks(node.decorator_list)))
        segment = ast.get_source_segment(source, node) or ""
        result.append(
            {
                "test_name": node.name,
                "nodeid": f"{relative}::{owner}::{node.name}" if owner else f"{relative}::{node.name}",
                "file": relative,
                "marks": ";".join(marks),
                "title": _title(node),
                "calls": ";".join(dict.fromkeys(_CALL_RE.findall(segment))),
                "line": node.lineno,
            }
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_method(node, file_marks, "")
        elif isinstance(node, ast.ClassDef):
            class_marks = list(dict.fromkeys(file_marks + _decorator_marks(node.decorator_list)))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_method(child, class_marks, node.name)
    return result


def collect_test_methods(test_root: str | Path) -> list[dict[str, Any]]:
    """扫描 test_case/**/*.py，返回可写入 test_methods 的记录。"""
    root = Path(test_root).resolve()
    if not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        records.extend(_record_file(path, root, tree))
    return records
