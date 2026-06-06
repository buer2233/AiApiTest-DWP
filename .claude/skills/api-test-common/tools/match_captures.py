# -*- coding: utf-8 -*-

"""读取 runtime/latest.jsonl 和 URL 索引，生成 runtime/capture_selection.md。"""

import argparse
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime
from typing import List, Optional


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(TOOLS_DIR)
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from skill_utils.api_index_db import get_default_db_path, load_methods  # noqa: E402
from skill_utils.api_path_match import api_path_matches  # noqa: E402
from skill_utils.project_root import get_temp_dir, resolve_project_root  # noqa: E402


INDEX_DB_PATH = get_default_db_path(TOOLS_DIR)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def _resolve_repo_root() -> Optional[str]:
    return resolve_project_root(on_warn=_warn)


def _load_jsonl(path: str) -> List[dict]:
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _dedup_by_method_path(records: List[dict]) -> List[dict]:
    bucket = OrderedDict()
    for record in records:
        key = (record.get("method", ""), record.get("pure_path", ""))
        bucket[key] = record
    return list(bucket.values())


def _display_path(path: str, repo_root: str) -> str:
    try:
        return os.path.relpath(path, repo_root).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")


def _find_impl(methods: list[dict], pure_path: str, captured_method: str):
    matched = []
    captured_method = (captured_method or "").upper()
    for item in methods:
        method = (item.get("http_method") or item.get("method") or "").upper()
        if method and captured_method and method != captured_method:
            continue
        if api_path_matches(item.get("api_url") or item.get("pure_path") or "", pure_path):
            matched.append(item)
    return matched


def _render(records: List[dict], methods: list[dict], jsonl_path: str, index_path: str, repo_root: str) -> str:
    lines = [
        "# capture_selection（抓包选择草稿）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 抓包数据：`{_display_path(jsonl_path, repo_root)}`",
        f"- 索引来源：`{_display_path(index_path, repo_root)}`",
        f"- 抓包条目：{len(records)} 条（已按 method+path 去重）",
        "",
        "## 使用说明",
        "",
        "1. 本文件是 AI 生成的草稿，请勾选你希望写进用例的接口。",
        "2. `[x]` 表示默认勾选（通常是新接口），`[ ]` 表示不勾选（通常已实现）。",
        "3. 静态资源由抓包脚本过滤；二进制/文件响应默认不加入。",
        "4. 保存后告诉 AI \"已勾选\"，AI 将根据勾选结果生成方法与用例。",
        "",
        "## 需要加入用例的接口（请勾选）",
        "",
    ]

    normal_new = []
    normal_exist = []
    special = []
    for record in records:
        if record.get("body_skipped"):
            special.append(record)
            continue
        impls = _find_impl(methods, record.get("pure_path", ""), record.get("method", ""))
        if impls:
            normal_exist.append((record, impls))
        else:
            normal_new.append(record)

    lines.extend(["### 新接口（推荐勾选）", ""])
    if not normal_new:
        lines.append("_无_")
    for i, record in enumerate(normal_new, 1):
        lines.append(f"- [x] **{i}. {record.get('method', '?')} `{record.get('pure_path', '?')}`**")
        lines.append(f"  - 状态码：{record.get('status')}")
        lines.append(f"  - 完整 URL：`{record.get('url', '')}`")
        req_body = record.get("req_body")
        if req_body:
            req_body_short = req_body if len(req_body) <= 200 else req_body[:200] + "..."
            lines.append(f"  - 请求体（节选）：`{req_body_short}`")
    lines.append("")

    lines.extend(["### 已实现接口（默认不勾选）", ""])
    if not normal_exist:
        lines.append("_无_")
    for i, (record, impls) in enumerate(normal_exist, 1):
        lines.append(f"- [ ] **{i}. {record.get('method', '?')} `{record.get('pure_path', '?')}`**")
        for impl in impls[:3]:
            lines.append(
                f"  - 已实现：`{impl['file']}` → `{impl.get('class') or impl.get('class_name')}.{impl.get('api_name')}`"
            )
        if len(impls) > 3:
            lines.append(f"  - 另有 {len(impls) - 3} 处实现，详见索引")
    lines.append("")

    lines.extend(["## 特殊处理接口（二进制/文件响应）", ""])
    if not special:
        lines.append("_无_")
    for i, record in enumerate(special, 1):
        lines.append(f"- [ ] **{i}. {record.get('method', '?')} `{record.get('pure_path', '?')}`** ⚠️ {record.get('skip_reason', '')}")
        lines.append(f"  - 状态码：{record.get('status')}")
        lines.append(f"  - Content-Type：{record.get('resp_content_type', '')}")
    lines.append("")
    lines.append("_勾选完成后，告诉 AI “已勾选”即可继续生成。_")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", default=None, help="抓包 JSONL 路径（默认 runtime/latest.jsonl）")
    parser.add_argument("--out", default=None, help="输出草稿路径（默认 runtime/capture_selection.md）")
    parser.add_argument("--db", default=INDEX_DB_PATH, help="SQLite 索引路径")
    args = parser.parse_args()

    repo_root = _resolve_repo_root()
    if not repo_root:
        print("ERROR: 未找到项目根，请确认 skill 安装在 <project>/.claude/skills/api-test-common/ 路径下。", file=sys.stderr)
        return 1
    runtime_dir = get_temp_dir(on_warn=_warn)
    if not runtime_dir:
        return 1

    jsonl_path = args.jsonl or os.path.join(runtime_dir, "latest.jsonl")
    out_md = args.out or os.path.join(runtime_dir, "capture_selection.md")
    methods = load_methods(args.db)
    if not methods:
        print("WARN: page_api_index.sqlite3 为空或缺失，请先运行 scan_page_api.py", file=sys.stderr)

    records = _dedup_by_method_path(_load_jsonl(jsonl_path))
    if not records:
        print(f"WARN: 抓包数据为空 -> {jsonl_path}", file=sys.stderr)

    content = _render(records, methods, jsonl_path, args.db, repo_root)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[match_captures] records={len(records)} -> {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
