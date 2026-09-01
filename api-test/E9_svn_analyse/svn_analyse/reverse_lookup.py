# -*- coding: utf-8 -*-
"""四期 T4.2：代码反查证据包（reverse_lookup.json）。

把阶段 A 的 impact/callers、HTTP 端点、源码位置、参数契约和前端操作
证据串成一份版本化 JSON，供 design.json 引用与阶段 B 决策。证据只引用
相对路径、符号、行号和脱敏摘要，不写完整源码、凭据或敏感响应。

证据来源标记（evidence.source）：
- ``mcp_callers``：外部 MCP callers 查询；
- ``static_scan``：code_repo 静态扫描（调用方/前端 URL）；
- ``endpoint_diagnostics``：阶段 A 端点提取诊断。

前端操作置信度（confidence）取值遵循需求分析约定：
``static`` / ``runtime`` / ``confirmed`` / ``conflict``。静态扫描未命中
的端点不伪造条目，记入 ``frontend_scan.misses``，等待运行时证据补充。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from svn_analyse import facts as facts_mod

SCHEMA_VERSION = "t4.2-v1"

CONFIDENCE_STATIC = "static"
CONFIDENCE_RUNTIME = "runtime"
CONFIDENCE_CONFIRMED = "confirmed"
CONFIDENCE_CONFLICT = "conflict"
VALID_CONFIDENCE = {
    CONFIDENCE_STATIC,
    CONFIDENCE_RUNTIME,
    CONFIDENCE_CONFIRMED,
    CONFIDENCE_CONFLICT,
}

EVIDENCE_MCP = "mcp_callers"
EVIDENCE_STATIC = "static_scan"

# 前端静态扫描的范围与体量上限（全库 grep 实测超过分钟级，必须限界）
FRONTEND_EXTS = {".jsp", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".ftl", ".vue"}
FRONTEND_SCAN_MAX_ROOTS = 8
FRONTEND_SCAN_MAX_FILES = 6000
FRONTEND_SCAN_MAX_FILE_BYTES = 768 * 1024
EXCLUDED_SCAN_DIRS = {
    "src",
    "classbean",
    "web-inf",
    ".svn",
    ".git",
    "node_modules",
    "report",
    "runtime",
    "logs",
}
# URL 段作为前端目录候选时的最小长度，避免 api/yd 这类短词误匹配
MIN_SEGMENT_LEN = 3

_CALLER_LINE = re.compile(r"^\s*(?:[\w.<>,\[\]?@\s]+\s+)?(\w+)\s*\(")
_HTTP_MARK = re.compile(r"fetch\s*\(|ajax\s*\(|\$\.post|\$\.get|axios|XMLHttpRequest|\.post\s*\(|\.get\s*\(", re.I)
_TRIGGER_MARK = re.compile(r"on(click|submit|change|blur|keyup)\s*=|\.click\s*\(|\.submit\s*\(|bind\s*\(\s*['\"](?:click|submit|change)", re.I)


def _role_from_path(path: str) -> str:
    """按 E9 目录约定推断调用链节点角色。"""
    lower = (path or "").lower()
    if "/controller/" in lower or "/web/" in lower:
        return "entry"
    if "/service/" in lower:
        return "service"
    if "/util/" in lower or "/utils/" in lower:
        return "util"
    if "/entity/" in lower or "/bean/" in lower:
        return "entity"
    return "other"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_callers_text(text: str) -> list[dict[str, Any]]:
    """把外部 MCP callers 返回文本解析成结构化条目。

    MCP 输出形如：

    - ``**Callers of X — N distinct definitions ...**``：标题行，跳过；
    - ``**pkg::Name** (class) — file:line``：定义行，保留（查询符号自身
      在 build_call_chain 里剔除）；
    - ``- pkg.path (namespace) - file:line — via import``：调用方条目，
      带项目符号前缀与可选的 ``via <关系>`` 后缀；
    - ``- (no callers)``：空结果标记，跳过。

    返回 ``[{"symbol", "kind", "file", "line", "relation"}]``，去重保序。
    """
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    bullet = re.compile(r"^[-•·]\s+")
    tail = r"(?::(\d+))?(?:\s*[—\-]+\s*via\s+([\w ]+?))?\s*$"
    bold_pattern = re.compile(
        r"^\*\*(?:[\w.$]+::)?([\w.$]+)\*\*\s*\((\w+)\)\s*[—\-]+\s*(\S+?)" + tail
    )
    plain_pattern = re.compile(
        r"^([\w.$]+)\s*\((\w+)\)\s*[—\-]+\s*(\S+?)" + tail
    )
    for raw in (text or "").splitlines():
        line = bullet.sub("", (raw or "").strip()).strip()
        if not line or line == "(no callers)" or line.startswith("**Callers of"):
            continue
        match = bold_pattern.match(line) or plain_pattern.match(line)
        if not match:
            continue
        symbol, kind, file_path = match.group(1), match.group(2), match.group(3)
        line_no = int(match.group(4) or 0)
        relation = (match.group(5) or "").strip()
        if kind == "file":
            # 文件级定义行对调用链无信息量
            continue
        key = (symbol, file_path, line_no)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "symbol": symbol,
                "kind": kind,
                "file": file_path,
                "line": line_no,
                "relation": relation,
            }
        )
    return entries


def build_call_chain(
    repo: Path,
    symbol: str,
    changed_path: str,
    graph: Any = None,
    read_text=None,
    max_static_callers: int = 8,
) -> tuple[list[dict[str, Any]], list[str]]:
    """为单个变更符号构建调用链证据，返回 (call_chain, degraded_notes)。

    优先使用 MCP callers（evidence=mcp_callers），再叠加静态
    扫描的调用方与行号（evidence=static_scan）。MCP 不可用时仅用
    静态结果并在 degraded_notes 说明，不中断。
    """
    reader = read_text or _read_text
    chain: list[dict[str, Any]] = []
    notes: list[str] = []

    if graph is not None:
        try:
            text = graph.callers(repo, symbol)
            for parsed in parse_callers_text(text):
                parsed_name = parsed["symbol"].split(".")[-1]
                if parsed_name == symbol or parsed["symbol"] == symbol:
                    # 定义行/查询符号自身不属于调用链
                    continue
                if any(item["symbol"] == parsed["symbol"] for item in chain):
                    continue
                chain.append(
                    {
                        "order": len(chain) + 1,
                        "symbol": parsed["symbol"],
                        "file": parsed["file"],
                        "line": parsed["line"],
                        "relation": parsed.get("relation") or "",
                        "role": _role_from_path(parsed["file"]) if parsed["file"] else "caller",
                        "evidence": EVIDENCE_MCP,
                    }
                )
        except Exception as exc:  # noqa: BLE001 — MCP 不可用降级为纯静态
            notes.append(f"外部 MCP callers 查询失败，调用链仅含静态扫描: {exc}")

    # 静态扫描补齐文件与行号（T4.1 的逐级范围复用）
    static_hits: list[str] = []
    for scope in facts_mod.caller_scan_scopes(changed_path):
        static_hits = facts_mod.find_caller_files_in_scope(
            repo, scope, symbol, changed_path, read_text=reader,
            max_matches=max_static_callers,
        )
        if static_hits:
            break
    for rel in static_hits:
        text = reader(repo / rel)
        line_no = _find_reference_line(text, symbol)
        static_class = facts_mod.class_name_from_path(rel) or ""
        known = next(
            (
                item
                for item in chain
                if (item.get("file") and item["file"] == rel)
                or (
                    static_class
                    and item["symbol"].split(".")[-1].split("::")[-1] == static_class
                )
            ),
            None,
        )
        if known is not None:
            if not known.get("file"):
                known["file"] = rel
            if not known.get("line"):
                known["line"] = line_no
            if known.get("role") == "caller":
                known["role"] = _role_from_path(rel)
            continue
        chain.append(
            {
                "order": len(chain) + 1,
                "symbol": static_class or rel,
                "file": rel,
                "line": line_no,
                "role": _role_from_path(rel),
                "evidence": EVIDENCE_STATIC,
            }
        )
    return chain, notes


def _find_reference_line(text: str, symbol: str) -> int:
    """返回符号首次被引用（非 import/package 行）的行号，找不到为 0。"""
    pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
    for index, line in enumerate((text or "").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("import ", "package ")):
            continue
        if pattern.search(line):
            return index
    return 0


def extract_parameter_contract(source: str, method_name: str) -> tuple[list[dict[str, str]], int]:
    """从方法签名提取参数契约（类型 + 名称），返回 (参数列表, 声明行号)。"""
    pattern = re.compile(
        r"(?:public|protected|private)[^;{]*\b" + re.escape(method_name) + r"\s*\(([^)]*)\)",
        re.S,
    )
    match = pattern.search(source or "")
    if not match:
        return [], 0
    line_no = (source or "").count("\n", 0, match.start()) + 1
    params: list[dict[str, str]] = []
    raw = match.group(1) or ""
    depth = 0
    piece = ""
    for char in raw:
        if char in "<(":
            depth += 1
        elif char in ">)":
            depth -= 1
        if char == "," and depth == 0:
            params.append(_parse_single_param(piece))
            piece = ""
        else:
            piece += char
    if piece.strip():
        params.append(_parse_single_param(piece))
    return [item for item in params if item["name"]], line_no


def _parse_single_param(piece: str) -> dict[str, str]:
    """拆单个参数：去掉注解，保留类型与名称。"""
    text = re.sub(r"@\w+(?:\([^)]*\))?", "", piece).strip()
    tokens = [token for token in text.split() if token]
    if len(tokens) >= 2:
        return {"type": " ".join(tokens[:-1]), "name": tokens[-1]}
    if tokens:
        return {"type": "", "name": tokens[0]}
    return {"type": "", "name": ""}


def collect_endpoint_contracts(
    repo: Path,
    endpoints: Iterable[dict[str, Any]],
    read_text=None,
) -> list[dict[str, Any]]:
    """为每个端点的入口方法提取参数契约与源码位置。"""
    reader = read_text or _read_text
    contracts: list[dict[str, Any]] = []
    cache: dict[str, str] = {}
    for endpoint in endpoints:
        action = endpoint.get("action") or ""
        method_name = action.split(".")[-1] if action else ""
        rel = endpoint.get("source_file") or ""
        if not method_name or not rel:
            continue
        if rel not in cache:
            cache[rel] = reader(repo / rel)
        source = cache[rel]
        parameters, line_no = extract_parameter_contract(source, method_name)
        contracts.append(
            {
                "endpoint": f"{endpoint.get('method')} {endpoint.get('url')}",
                "action": action,
                "file": rel,
                "line": line_no,
                "parameters": parameters,
            }
        )
    return contracts


def _candidate_frontend_roots(repo: Path, urls: list[str]) -> list[Path]:
    """按端点 URL 段挑选前端扫描目录：等值或前缀匹配顶层目录，另加 wui。"""
    segments: set[str] = set()
    for url in urls:
        for part in (url or "").split("/"):
            part = part.strip()
            if len(part) >= MIN_SEGMENT_LEN and part != "api":
                segments.add(part.lower())
    roots: list[Path] = []
    seen: set[str] = set()
    wui = repo / "wui"
    if wui.is_dir():
        roots.append(wui)
        seen.add("wui")
    if not segments:
        return roots
    try:
        entries = sorted([entry for entry in repo.iterdir() if entry.is_dir()])
    except OSError:
        return roots
    for entry in entries:
        if len(roots) >= FRONTEND_SCAN_MAX_ROOTS:
            break
        name = entry.name.lower()
        if name in seen or name in EXCLUDED_SCAN_DIRS or name.startswith("."):
            continue
        if any(name == segment or name.startswith(segment) for segment in segments):
            roots.append(entry)
            seen.add(name)
    return roots


def scan_frontend_operations(
    repo: Path,
    endpoints: Iterable[dict[str, Any]],
    read_text=None,
    max_files: int = FRONTEND_SCAN_MAX_FILES,
) -> dict[str, Any]:
    """静态扫描前端文件，建立「页面操作 → 接口」证据。

    命中规则（任一）：端点去 /api 前缀后的完整路径；路径最后两段；
    方法名与 HTTP 请求标记同现。每条命中给出一条 frontend_operation，
    confidence=static；未命中的端点记入 misses，不伪造证据。
    扫描目录按 URL 段挑选并受数量/体量上限约束。
    """
    reader = read_text or _read_text
    endpoint_list = list(endpoints)
    urls = [str(item.get("url") or "") for item in endpoint_list]
    roots = _candidate_frontend_roots(repo, urls)
    needles: dict[str, list[dict[str, Any]]] = {}
    for endpoint in endpoint_list:
        url = str(endpoint.get("url") or "")
        trimmed = url[4:] if url.startswith("/api") else url
        parts = [part for part in trimmed.split("/") if part]
        candidates = {trimmed, "/".join(parts[-2:]) if len(parts) >= 2 else trimmed}
        if parts:
            candidates.add(parts[-1])
        needles.setdefault(url, [])
        endpoint.setdefault("_needles", candidates)

    operations: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    scanned_files = 0
    hit_urls: set[str] = set()
    for root in roots:
        if scanned_files >= max_files:
            break
        for path in sorted(root.rglob("*")):
            if scanned_files >= max_files:
                break
            if not path.is_file() or path.suffix.lower() not in FRONTEND_EXTS:
                continue
            if any(part.lower() in EXCLUDED_SCAN_DIRS for part in path.parts):
                continue
            try:
                if path.stat().st_size > FRONTEND_SCAN_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            scanned_files += 1
            text = reader(path)
            if not text:
                continue
            rel = str(path.relative_to(repo)).replace("\\", "/")
            lines = text.splitlines()
            for endpoint in endpoint_list:
                url = str(endpoint.get("url") or "")
                hit_lines: set[int] = set()
                for needle in sorted(endpoint.get("_needles", set()), key=len, reverse=True):
                    if not needle:
                        continue
                    bare = needle.split("/")[-1]
                    for index, line in enumerate(lines, start=1):
                        if index in hit_lines or needle not in line:
                            continue
                        if needle == bare and not _HTTP_MARK.search(line):
                            # 仅方法名命中时，要求同行存在请求标记，降低误报
                            continue
                        hit_lines.add(index)
                        trigger = _find_trigger(lines, index)
                        operations.append(
                            {
                                "operation": endpoint.get("action") or url,
                                "page": rel,
                                "trigger": trigger,
                                "request": {
                                    "method": endpoint.get("method") or "",
                                    "url": url,
                                },
                                "parameters": [],
                                "response_effect": "",
                                "evidence": {
                                    "source": EVIDENCE_STATIC,
                                    "file": rel,
                                    "line": index,
                                    "matched": needle,
                                },
                                "confidence": CONFIDENCE_STATIC,
                            }
                        )
                        hit_urls.add(url)
                        break
    for endpoint in endpoint_list:
        endpoint.pop("_needles", None)
        url = str(endpoint.get("url") or "")
        if url not in hit_urls:
            misses.append(
                {
                    "endpoint": f"{endpoint.get('method')} {url}",
                    "note": "静态扫描未命中；URL 可能动态拼接或由独立前端应用发起，需浏览器 Network/HAR 运行时证据确认",
                }
            )
    return {
        "operations": operations,
        "misses": misses,
        "scanned_roots": [str(item.relative_to(repo)).replace("\\", "/") for item in roots],
        "scanned_files": scanned_files,
    }


def _find_trigger(lines: list[str], hit_line: int) -> str:
    """在命中行附近 ±5 行内寻找事件触发器标记。"""
    start = max(0, hit_line - 6)
    end = min(len(lines), hit_line + 5)
    for line in lines[start:end]:
        match = _TRIGGER_MARK.search(line)
        if match:
            return match.group(0).strip()
    return ""


def check_coverage_consistency(
    reverse_lookup: dict[str, Any],
    existing_api: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """比较反查端点与 api-test-E9 已有封装/用例，输出覆盖一致性结论。"""
    existing = existing_api or []

    def _wrapper_for(url: str) -> dict[str, Any]:
        for item in existing:
            if item.get("url") == url and (item.get("wrapper") or item.get("tests")):
                return item
        return {}

    entries = []
    uncovered = []
    for endpoint in reverse_lookup.get("entries") or []:
        url = endpoint.get("url") or ""
        hit = _wrapper_for(url)
        tests = hit.get("tests") or []
        status = "covered_by_test" if tests else ("covered_by_wrapper" if hit else "uncovered")
        entries.append(
            {
                "endpoint": f"{endpoint.get('method')} {url}",
                "status": status,
                "wrapper": hit.get("wrapper") or "",
                "tests": tests,
            }
        )
        if status == "uncovered":
            uncovered.append(f"{endpoint.get('method')} {url}")
    return {
        "consistent": not uncovered,
        "entries": entries,
        "uncovered_endpoints": uncovered,
    }


def build_reverse_lookup(
    repo: Path,
    facts: dict[str, Any],
    graph: Any = None,
    read_text=None,
) -> dict[str, Any]:
    """汇总阶段 A 事实，生成版本化反查证据包。"""
    endpoints = list(facts.get("endpoints") or [])
    symbols = list(facts.get("symbols") or [])
    changed_files = list(facts.get("changed_files") or [])
    degraded_notes: list[str] = []
    if facts.get("pure_frontend"):
        degraded_notes.append("纯前端提交：未执行后端调用链反查。")
    elif graph is None:
        degraded_notes.append("未启用 MCP callers 查询（--skip-mcp），调用链仅基于静态扫描。")

    symbol_entries: list[dict[str, Any]] = []
    for symbol in symbols:
        name = symbol.get("name") or ""
        changed_path = symbol.get("file") or ""
        if not changed_path:
            match = next(
                (item for item in changed_files if facts_mod.class_name_from_path(item.get("path") or "") == name),
                {},
            )
            changed_path = match.get("path") or ""
        chain, notes = (
            ([], ["纯前端提交跳过调用链反查"])
            if facts.get("pure_frontend")
            else build_call_chain(repo, name, changed_path, graph=graph, read_text=read_text)
        )
        degraded_notes.extend(notes)
        related_endpoints = [
            {
                "method": item.get("method"),
                "url": item.get("url"),
                "action": item.get("action"),
                "via": item.get("via") or "direct",
                "evidence": item.get("prompted_by") or item.get("via") or "direct",
            }
            for item in endpoints
            if name and (name in (item.get("action") or "") or _linked_by_chain(item, chain))
        ]
        symbol_entries.append(
            {
                "name": name,
                "kind": symbol.get("kind") or "",
                "changed_file": changed_path,
                "entries": related_endpoints,
                "call_chain": chain,
            }
        )

    contracts = (
        []
        if facts.get("pure_frontend")
        else collect_endpoint_contracts(repo, endpoints, read_text=read_text)
    )
    frontend_scan = (
        {"operations": [], "misses": [], "scanned_roots": [], "scanned_files": 0,
         "note": "纯前端提交无需反查前端操作证据"}
        if facts.get("pure_frontend")
        else scan_frontend_operations(repo, endpoints, read_text=read_text)
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "revision": facts.get("revision"),
        "generated_by": "svn_analyse.reverse_lookup",
        "degraded": {
            "mcp_available": graph is not None and not any(
                "调用链仅含静态扫描" in note for note in degraded_notes
            ),
            "notes": degraded_notes,
        },
        "symbols": symbol_entries,
        "entries": [
            {
                "method": item.get("method"),
                "url": item.get("url"),
                "action": item.get("action"),
                "via": item.get("via") or "direct",
                "source_file": item.get("source_file") or "",
            }
            for item in endpoints
        ],
        "contracts": contracts,
        "frontend_scan": frontend_scan,
        "frontend_operations": frontend_scan.get("operations") or [],
        "diagnostics_ref": "facts.json#endpoint_diagnostics",
        "endpoint_diagnostics": facts.get("endpoint_diagnostics") or {},
    }
    payload["coverage_consistency"] = check_coverage_consistency(
        payload, facts.get("existing_api") or []
    )
    return payload


def _linked_by_chain(endpoint: dict[str, Any], chain: list[dict[str, Any]]) -> bool:
    """端点 action 的类名与调用链节点互相引用时视为关联。"""
    action_class = (endpoint.get("action") or "").split(".")[0]
    if not action_class:
        return False
    return any(
        action_class in (item.get("symbol") or "") or (item.get("file") or "").endswith(f"{action_class}.java")
        for item in chain
    )


def write_reverse_lookup(out_dir: str | Path, payload: dict[str, Any]) -> Path:
    dest = Path(out_dir) / "reverse_lookup.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def load_reverse_lookup(out_dir: str | Path) -> dict[str, Any]:
    path = Path(out_dir) / "reverse_lookup.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
