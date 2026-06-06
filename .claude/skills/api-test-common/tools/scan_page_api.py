# -*- coding: utf-8 -*-

"""扫描 test_case/page_api 下所有接口方法，写入 tools/page_api_index.sqlite3。"""

import argparse
import ast
import os
import re
import sys
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple


for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(TOOLS_DIR)
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from skill_utils.api_index_db import (  # noqa: E402
    existing_url_method_pairs,
    get_default_db_path,
    insert_methods,
    is_empty,
    replace_index,
)
from skill_utils.common_function import update_skill_config  # noqa: E402
from skill_utils.project_root import resolve_project_root  # noqa: E402


INDEX_DB_PATH = get_default_db_path(TOOLS_DIR)
SCANNER_VERSION = "2026-06-03-common-incremental-v1"
RECENT_DAYS = 30
APIDATA_UPDATE_FIELD = "apiDataUpdateDate"

URL_EXTRACT_RULES = [
    {
        "name": "quoted_http_url",
        "pattern": re.compile(r"(?i)(?:[rubf]*)(['\"])https?://[^'\"]+?(/[^'\"?\s]*(?:\?[^'\"]+)?)\1"),
        "group": 2,
    },
    {
        "name": "url_assignment_path_literal",
        "pattern": re.compile(r"(?i)\burl\s*=\s*(?:[rubf]*)(['\"])(/[^'\"?\s]*(?:\?[^'\"]+)?)\1"),
        "group": 2,
    },
    {
        "name": "build_url_path_literal",
        "pattern": re.compile(r"(?i)\bbuild_url\(\s*(?:[rubf]*)(['\"])(/[^'\"?\s]*(?:\?[^'\"]+)?)\1"),
        "group": 2,
    },
]
REQUEST_METHOD_RULES = [
    re.compile(r"\.request\(\s*['\"]([A-Za-z]+)['\"]"),
    re.compile(r"requests\.request\(\s*['\"]([A-Za-z]+)['\"]"),
    re.compile(r"requests\.(get|post|put|delete|patch|head|options)\(", re.IGNORECASE),
    re.compile(r"\.(get|post|put|delete|patch|head|options)\(", re.IGNORECASE),
]
META_COMMENT_RE = re.compile(r"^\s*#\s*(Author|Create Date|Update Date)\s*[:：]\s*(.*?)\s*$", re.IGNORECASE)
DATE_PREFIX_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")


def _warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _resolve_repo_root() -> Optional[str]:
    return resolve_project_root(on_warn=_warn)


def _clean_url_path(path: str) -> str:
    value = (path or "").strip().strip("'\"")
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        match = re.match(r"https?://[^/]+(/.*)?", value)
        value = match.group(1) if match and match.group(1) else "/"
    value = value.split("?", 1)[0]
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/") or "/"


def _unique_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _extract_urls_from_source(source: str) -> List[str]:
    urls = []
    for rule in URL_EXTRACT_RULES:
        for match in rule["pattern"].finditer(source):
            urls.append(_clean_url_path(match.group(rule["group"])))
    return _unique_keep_order(urls)


def _get_bases(node: ast.ClassDef) -> List[str]:
    bases = []
    for base in node.bases:
        try:
            bases.append(ast.unparse(base))
        except Exception:
            bases.append(getattr(base, "id", "?"))
    return bases


def _extract_doc_desc(func: ast.AST) -> str:
    doc = ast.get_docstring(func) or ""
    lines = [line.strip() for line in doc.splitlines() if line.strip()]
    for line in lines:
        match = re.match(r"^(?:desc|description|描述)\s*[:：]\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    for line in lines:
        if line.startswith(":") or line.startswith("@"):
            continue
        return line
    return ""


def _extract_comment_meta(body_text: str) -> Dict[str, str]:
    meta = {"author": "", "create_date": "", "update_date": ""}
    key_map = {"author": "author", "create date": "create_date", "update date": "update_date"}
    for line in body_text.splitlines():
        match = META_COMMENT_RE.match(line)
        if match:
            meta[key_map[match.group(1).lower()]] = match.group(2).strip()
    return meta


def _extract_http_method(body_text: str) -> str:
    for rule in REQUEST_METHOD_RULES:
        match = rule.search(body_text)
        if match:
            return match.group(1).upper()
    return ""


def _parse_create_date(value: str) -> Optional[date]:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    match = DATE_PREFIX_RE.match(raw)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def _parse_file(path: str) -> List[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
    except Exception:
        return []

    src_lines = source.splitlines()
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            start = sub.lineno - 1
            end = getattr(sub, "end_lineno", sub.lineno) or sub.lineno
            body_text = "\n".join(src_lines[start:end])
            urls = _unique_keep_order(_extract_urls_from_source(body_text))
            if not urls:
                continue
            meta = _extract_comment_meta(body_text)
            http_method = _extract_http_method(body_text)
            for url in urls:
                results.append({
                    "class": node.name,
                    "bases": _get_bases(node),
                    "method": sub.name,
                    "api_name": sub.name,
                    "api_desc": _extract_doc_desc(sub),
                    "author": meta["author"],
                    "create_date": meta["create_date"],
                    "update_date": meta["update_date"],
                    "http_method": http_method,
                    "url_literal": url,
                    "pure_path": url,
                    "api_url": url,
                    "line": sub.lineno,
                })
    return results


def _iter_api_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py") and not filename.startswith("__"):
                yield os.path.join(dirpath, filename)


def _scan_all(repo_root: str, page_api_root: str) -> Tuple[List[dict], int]:
    records = []
    scanned = 0
    for fp in _iter_api_files(page_api_root):
        scanned += 1
        rel = os.path.relpath(fp, repo_root).replace("\\", "/")
        mtime = int(os.path.getmtime(fp))
        for item in _parse_file(fp):
            item["file"] = rel
            item["mtime"] = mtime
            records.append(item)
    return records, scanned


def _filter_recent(records: List[dict], days: int) -> List[dict]:
    cutoff = date.today() - timedelta(days=days)
    return [
        item for item in records
        if (parsed := _parse_create_date(item.get("create_date") or "")) and parsed >= cutoff
    ]


def _filter_truly_new(records: List[dict], existing_pairs: Set[Tuple[str, str]]) -> List[dict]:
    batch_seen = set()
    new_items = []
    for item in records:
        api_url = (item.get("api_url") or "").strip()
        method = (item.get("http_method") or "").strip().upper()
        if not api_url or (api_url, method) in existing_pairs:
            continue
        dedup_key = (api_url, method, item.get("file") or "", int(item.get("line") or 0))
        if dedup_key in batch_seen:
            continue
        batch_seen.add(dedup_key)
        new_items.append(item)
    return new_items


def _build_metadata(repo_root: str, page_api_root: str, scanned: int, total: int, unique: int, mode: str) -> Dict[str, str]:
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repo_root": repo_root.replace("\\", "/"),
        "page_api_root": os.path.relpath(page_api_root, repo_root).replace("\\", "/"),
        "scanner_version": SCANNER_VERSION,
        "scanned_files": str(scanned),
        "total_methods": str(total),
        "unique_paths": str(unique),
        "scan_mode": mode,
    }


def _print_new_method_summary(new_items: List[dict]) -> None:
    print(f"[scan_page_api] recent_new_methods_count={len(new_items)}")
    if not new_items:
        return
    print("[scan_page_api] recent_new_methods:")
    for item in new_items:
        api_name = item.get("api_name") or item.get("method") or ""
        api_url = item.get("api_url") or ""
        http_method = (item.get("http_method") or "").upper() or "-"
        print(f"  - {http_method} {api_url} :: {api_name}")


def _update_apidata_date() -> None:
    today_str = date.today().strftime("%Y-%m-%d")
    if not update_skill_config({APIDATA_UPDATE_FIELD: today_str}, on_warn=_warn, on_info=_info):
        _warn(f"未能写入 {APIDATA_UPDATE_FIELD}={today_str} 到 config.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="强制全量替换，忽略增量模式")
    parser.add_argument("--db", default=INDEX_DB_PATH, help="SQLite 索引路径")
    args = parser.parse_args()

    repo_root = _resolve_repo_root()
    if not repo_root:
        print("ERROR: 未找到项目根，请确认 skill 安装在 <project>/.claude/skills/api-test-common/ 路径下。", file=sys.stderr)
        return 1

    page_api_root = os.path.join(repo_root, "test_case", "page_api")
    if not os.path.isdir(page_api_root):
        print(f"ERROR: 未找到 page_api 目录 {page_api_root}", file=sys.stderr)
        return 1

    force_full = args.full or is_empty(args.db)
    all_records, scanned = _scan_all(repo_root, page_api_root)
    unique_paths = len({item.get("api_url") for item in all_records if item.get("api_url")})

    if force_full:
        metadata = _build_metadata(repo_root, page_api_root, scanned, len(all_records), unique_paths, "full")
        replace_index(args.db, all_records, metadata)
        _print_new_method_summary([])
        _update_apidata_date()
        print(f"[scan_page_api] mode=full scanned={scanned} methods={len(all_records)} unique_paths={unique_paths} -> {args.db}")
        return 0

    existing_pairs = existing_url_method_pairs(args.db)
    recent_records = _filter_recent(all_records, RECENT_DAYS)
    new_items = _filter_truly_new(recent_records, existing_pairs)
    metadata = _build_metadata(repo_root, page_api_root, scanned, len(all_records), unique_paths, "incremental")
    inserted = insert_methods(args.db, new_items, metadata)
    _print_new_method_summary(new_items)
    _update_apidata_date()
    print(f"[scan_page_api] mode=incremental scanned={scanned} recent={len(recent_records)} new_inserted={inserted} -> {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
