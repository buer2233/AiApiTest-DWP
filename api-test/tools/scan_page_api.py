"""按 E9 简化规则扫描 page_api 接口封装并维护 SQLite 索引。"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# 直接执行 tools 脚本时，按文件位置补齐项目根以导入同级 skill_utils。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from skill_utils.api_index_db import (
    existing_url_method_pairs,
    get_default_db_path,
    insert_methods,
    is_empty,
    replace_index,
)
from skill_utils.project_root import resolve_project_root


# E9 仅保留 URL 赋值与 self HTTP 调用两条提取规则。
URL_RE = re.compile(r"url\s*=\s*['\"](/[^'\"]+)['\"]")
HTTP_METHOD_RE = re.compile(r"self\.(get|post|put|delete)\s*\(", re.IGNORECASE)
_METADATA_RE = {
    "author": re.compile(r"^\s*#\s*(?:Author|作者)\s*[:：]\s*(.+?)\s*$", re.IGNORECASE),
    "create_date": re.compile(
        r"^\s*#\s*(?:Create\s*Date|创建日期)\s*[:：]\s*(.+?)\s*$", re.IGNORECASE
    ),
    "is_ai": re.compile(
        r"^\s*#\s*(?:IsAI|是否由\s*AI\s*生成)\s*[:：]\s*(.+?)\s*$", re.IGNORECASE
    ),
}


@dataclass(frozen=True)
class ScanResult:
    """封装扫描和索引写入的结构化结果。"""

    records: list[dict[str, object]]
    warnings: list[str] = field(default_factory=list)
    mode: str = "scan"
    inserted: int = 0

    def as_dict(self) -> dict[str, object]:
        """转换为可直接输出的 JSON 兼容字典。"""
        return asdict(self)


def _first_docstring_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """提取方法文档字符串的第一条非空说明。"""
    docstring = ast.get_docstring(node, clean=True) or ""
    for line in docstring.splitlines():
        text = line.strip()
        if text:
            return text
    return ""


def _allure_step(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """读取 @allure.step 装饰器中的固定文本，未找到时返回空字符串。"""
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not decorator.args:
            continue
        if not (
            isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "allure"
            and decorator.func.attr == "step"
        ):
            continue
        first_arg = decorator.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value.strip()
    return ""


def _metadata(source_lines: list[str], node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    """在方法源码范围内提取 E9 规定的三项元数据。"""
    start = max(node.lineno - 1, 0)
    end = min(node.end_lineno or node.lineno, len(source_lines))
    values = {key: "" for key in _METADATA_RE}
    for line in source_lines[start:end]:
        for key, pattern in _METADATA_RE.items():
            match = pattern.match(line)
            if match:
                values[key] = match.group(1).strip()
    return values


def _class_bases(node: ast.ClassDef) -> list[str]:
    """返回类定义中可直接呈现的父类名称列表。"""
    names: list[str] = []
    for base in node.bases:
        try:
            names.append(ast.unparse(base))
        except AttributeError:
            if isinstance(base, ast.Name):
                names.append(base.id)
    return names


def _scan_method(
    *,
    path: Path,
    root: Path,
    source_lines: list[str],
    class_node: ast.ClassDef,
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[list[dict[str, object]], list[str]]:
    """扫描单个类方法并返回接口记录与非模板告警。"""
    start = max(method_node.lineno - 1, 0)
    end = min(method_node.end_lineno or method_node.lineno, len(source_lines))
    method_source = "\n".join(source_lines[start:end])
    urls = [match.group(1) for match in URL_RE.finditer(method_source)]
    http_methods = [match.group(1).upper() for match in HTTP_METHOD_RE.finditer(method_source)]
    if not urls:
        return [], []
    if not http_methods:
        return [], [f"{path}:{method_node.lineno} 跳过未匹配 self HTTP 调用的方法 {method_node.name}"]

    metadata = _metadata(source_lines, method_node)
    description = _first_docstring_line(method_node) or _allure_step(method_node)
    relative_file = path.relative_to(root).as_posix()
    common = {
        "api_name": method_node.name,
        "api_desc": description,
        "class_name": class_node.name,
        "class_bases": _class_bases(class_node),
        "file": relative_file,
        "line": method_node.lineno,
        "author": metadata["author"],
        "create_date": metadata["create_date"],
        "is_ai": metadata["is_ai"],
        "mtime": path.stat().st_mtime_ns,
    }
    records = [
        {**common, "api_url": url, "http_method": http_method}
        for url in urls
        for http_method in http_methods
    ]
    return records, []


def scan_page_api(page_api_root: str | Path) -> ScanResult:
    """扫描 page_api 下的 Python 封装，返回去重后的 E9 接口记录。"""
    root = Path(page_api_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"page_api 目录不存在：{root}")

    records: list[dict[str, object]] = []
    warnings: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            warnings.append(f"{path} 无法解析，已跳过：{exc}")
            continue
        source_lines = source.splitlines()
        for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for method_node in class_node.body:
                if not isinstance(method_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                method_records, method_warnings = _scan_method(
                    path=path,
                    root=root,
                    source_lines=source_lines,
                    class_node=class_node,
                    method_node=method_node,
                )
                warnings.extend(method_warnings)
                for record in method_records:
                    pair = (str(record["api_url"]), str(record["http_method"]))
                    if pair in seen_pairs:
                        warnings.append(
                            f"{path}:{method_node.lineno} 重复 URL/HTTP 方法 {pair[0]} {pair[1]}，已忽略"
                        )
                        continue
                    seen_pairs.add(pair)
                    records.append(record)
    return ScanResult(records=records, warnings=warnings)


def update_index(
    page_api_root: str | Path,
    db_path: str | Path | None = None,
    *,
    refresh: bool = False,
) -> ScanResult:
    """空库或显式刷新时全量替换，否则仅插入新增 URL/HTTP 方法组合。"""
    root = Path(page_api_root).resolve()
    path = Path(db_path) if db_path is not None else get_default_db_path(root.parent / "tools")
    scanned = scan_page_api(root)
    metadata = {"page_api_root": str(root), "record_count": len(scanned.records)}
    if refresh or is_empty(path):
        metadata["mode"] = "full"
        replace_index(path, scanned.records, metadata=metadata)
        return ScanResult(scanned.records, scanned.warnings, mode="full", inserted=len(scanned.records))

    existing = existing_url_method_pairs(path)
    new_records = [
        record
        for record in scanned.records
        if (str(record["api_url"]), str(record["http_method"])) not in existing
    ]
    metadata["mode"] = "incremental"
    inserted = insert_methods(path, new_records, metadata=metadata)
    return ScanResult(new_records, scanned.warnings, mode="incremental", inserted=inserted)


def _configure_stdout() -> None:
    """在支持的 Windows 终端强制 UTF-8 输出，避免中文路径和说明乱码。"""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def main() -> int:
    """提供独立的扫描和索引更新命令行入口。"""
    _configure_stdout()
    parser = argparse.ArgumentParser(description="扫描 E9 page_api 接口封装并更新索引。")
    parser.add_argument("--page-api-root", type=Path, help="待扫描的 page_api 目录。")
    parser.add_argument("--db", type=Path, help="SQLite 索引文件路径。")
    parser.add_argument("--refresh", action="store_true", help="强制全量替换已有索引。")
    args = parser.parse_args()
    project_root = resolve_project_root()
    page_api_root = args.page_api_root or project_root / "page_api"
    result = update_index(page_api_root, args.db, refresh=args.refresh)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
