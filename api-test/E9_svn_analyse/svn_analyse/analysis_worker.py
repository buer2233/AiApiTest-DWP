# -*- coding: utf-8 -*-
"""五期：单 revision 分析 worker（单笔与批次共用）。

从 ``cli.py`` 抽取，供 ``run_analyse()`` 和 ``batch_orchestrator`` 共同调用。
批次编排器逐 revision 调用本模块的 ``analyze_single_revision()``，每笔最多 3 次
attempt；单笔入口 ``run_analyse()`` 也委托本模块。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from svn_analyse import facts as facts_mod
from svn_analyse import inventory as inventory_mod
from svn_analyse import paths
from svn_analyse import coverage as coverage_mod
from svn_analyse import revision_meta
from svn_analyse import mcp_client
from svn_analyse import reverse_lookup as reverse_lookup_mod
from svn_analyse import report as report_mod
from svn_analyse.revision import parse_revision, revision_mark

# ── Trace 辅助 ────────────────────────────────────────────────────


def _trace_begin(trace: Any, revision: int, phase: str, step: str) -> str | None:
    if trace is None:
        return None
    try:
        return trace.begin_span(revision, phase, step)
    except Exception:
        return None


def _trace_end(trace: Any, revision: int, span_id: str | None, status: str = "ok", error_type: str = "") -> None:
    if trace is None or not span_id:
        return
    try:
        trace.end_span(revision, span_id, status=status, error_type=error_type)
    except Exception:
        pass


# ── 公共辅助函数 ──────────────────────────────────────────────────


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _fetch_temporal(ops: Any, revision: int) -> tuple[dict[str, Any], str, str, list[str]]:
    """从运维 MCP（或测试替身）取 log / diff；失败写入警告。"""
    warnings: list[str] = []
    log_info: dict[str, Any] = {"author": "", "date": "", "message": "", "paths": []}
    diff_text = ""
    working_rev = ""
    try:
        payload = ops.svn_log(revision)
        log_info = {
            "author": payload.get("author") or "",
            "date": payload.get("date") or "",
            "message": payload.get("message") or "",
            "paths": list(payload.get("paths") or []),
        }
        working_rev = str(payload.get("working_copy_revision") or "")
    except Exception as exc:
        warnings.append(f"MCP e9_svn_log 失败: {exc}")
    try:
        diff_payload = ops.svn_diff(revision)
        diff_text = str(diff_payload.get("diff") or "")
        if diff_payload.get("truncated"):
            warnings.append("e9_svn_diff 返回已截断")
    except Exception as exc:
        warnings.append(f"MCP e9_svn_diff 失败: {exc}")
    return log_info, diff_text, working_rev, warnings


def _changed_files(log_paths: list[dict[str, str]], diff_text: str, repo: Path) -> list[dict[str, str]]:
    """合并 log paths 和 diff 文件列表，去重并分类。"""
    files: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in log_paths:
        path = facts_mod.posix_path(item.get("path") or "")
        if not path or path in seen:
            continue
        seen.add(path)
        source = _safe_read(repo / path)
        files.append(
            {
                "path": path,
                "action": item.get("action") or "",
                "kind": facts_mod.classify_file(path, source),
                "change_layer": facts_mod.classify_change_layer(path),
            }
        )
    for path in facts_mod.parse_diff_files(diff_text):
        if path in seen:
            continue
        seen.add(path)
        source = _safe_read(repo / path)
        files.append(
            {
                "path": path,
                "action": "M",
                "kind": facts_mod.classify_file(path, source),
                "change_layer": facts_mod.classify_change_layer(path),
            }
        )
    return files


def _collect_graph(
    graph: Any,
    repo: Path,
    symbols: list[dict[str, str]],
    changed_files: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[str]]:
    """遍历符号，调用 MCP impact/callers，收集影响行和额外端点。"""
    warnings: list[str] = []
    impact_rows: list[dict[str, Any]] = []
    extra: list[dict[str, str]] = []
    changed_names = {item.get("name") for item in symbols}
    queried: set[str] = set()
    for symbol in symbols:
        name = symbol.get("name") or ""
        query = name.split(".")[0] if name else ""
        if not query or query in queried:
            continue
        queried.add(query)
        try:
            impact_text = graph.impact(repo, query)
            callers_text = ""
            try:
                callers_text = graph.callers(repo, query)
            except Exception as exc:
                warnings.append(f"mcp callers {query} 失败: {exc}")
            size = graph.parse_impact_size(impact_text)
            changed_this = query in changed_names or any(
                query in (item.get("name") or "") for item in symbols
            )
            note = "本次命中" if changed_this else "关联符号"
            defined_here = any(
                Path(item["path"]).stem == query for item in changed_files
            )
            if not defined_here and size:
                note = "本体未改，不扩散"
            impact_rows.append({"symbol": query, "size": size, "note": note})
            refs = graph.extract_action_refs((impact_text or "") + "\n" + (callers_text or ""))
            graph_endpoints = facts_mod.endpoints_from_action_refs(repo, refs)
            for item in graph_endpoints:
                item.setdefault("prompted_by", facts_mod.VIA_MCP)
            extra.extend(graph_endpoints)
        except Exception as exc:
            warnings.append(f"mcp impact {query} 失败: {exc}")
    return impact_rows, extra, warnings


def _merge_endpoints(
    left: list[dict[str, str]],
    right: list[dict[str, str]],
) -> list[dict[str, str]]:
    """合并两组端点，按 (method, url, action) 去重。"""
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for item in left + right:
        key = (item.get("method") or "", item.get("url") or "", item.get("action") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


# ── 关键事实判定 ──────────────────────────────────────────────────


def _collect_missing_key_facts(facts: dict[str, Any]) -> list[str]:
    """检查关键事实是否齐全，返回缺失项列表。"""
    missing: list[str] = []
    if not facts.get("message"):
        missing.append("提交说明缺失")
    if not facts.get("changed_files"):
        missing.append("变更文件列表缺失")
    if not facts.get("diff_excerpt"):
        missing.append("diff 内容缺失")
    java_symbols = [
        s for s in facts.get("symbols") or []
        if str(s.get("file") or "").lower().endswith(".java")
    ]
    if java_symbols and not facts.get("impact"):
        missing.append("图谱查询结论缺失")
    return missing


# ── 主 worker ─────────────────────────────────────────────────────


def analyze_single_revision(
    revision: int,
    root: Path,
    api_test_rel: str = "api-test-E9",
    output_root: str | Path | None = None,
    skip_mcp: bool = False,
    graph: Any = mcp_client,
    ops: Any = None,
    trace: Any = None,
) -> dict[str, Any]:
    """对单个 revision 执行完整分析，返回 facts 和产物路径。

    本函数是单笔和批次的公共 worker。批次编排器逐 revision 调用它，
    最多 3 次 attempt；单笔入口 ``run_analyse()`` 也委托给它。

    返回 dict：
    - ``revision``: int
    - ``mark``: str
    - ``status``: ``"complete"`` | ``"blocked"``
    - ``out_dir``: Path
    - ``paths``: dict[str, Path]
    - ``facts``: dict
    - ``attempts``: int
    - ``missing_key_facts``: list[str]
    """
    mark = revision_mark(revision)
    api_test = root / api_test_rel
    out_base = Path(output_root) if output_root else paths.output_root()
    out_dir = out_base / mark
    warnings: list[str] = []

    ops_client = ops if ops is not None else graph
    log_info, diff_text, working_rev, temporal_warnings = _fetch_temporal(ops_client, revision)
    warnings.extend(temporal_warnings)
    e9_root = root / "code_repo"
    if not e9_root.is_dir():
        e9_root = root
    changed_files = _changed_files(log_info.get("paths") or [], diff_text, e9_root)
    symbols: list[dict[str, str]] = [
        item
        for item in facts_mod.extract_symbols_from_diff(diff_text)
        if str(item.get("file") or "").lower().endswith(".java")
    ]

    pure_frontend = facts_mod.is_pure_frontend(changed_files)

    endpoints: list[dict[str, str]] = []
    impact_rows: list[dict[str, Any]] = []
    test_coverage: list[dict[str, Any]] = []
    endpoint_diag = facts_mod.new_endpoint_diagnostics(
        skipped="pure_frontend" if pure_frontend else None
    )

    if not pure_frontend:
        java_paths = [
            item.get("path") or ""
            for item in changed_files
            if str(item.get("path") or "").lower().endswith(".java")
        ]
        if java_paths:
            endpoints = facts_mod.endpoints_from_java_files(
                e9_root, java_paths, diagnostics=endpoint_diag
            )

    if not skip_mcp and not pure_frontend:
        graph_span = _trace_begin(trace, revision, "mcp_query", "impact_callers")
        impact_rows, extra_endpoints, graph_warnings = _collect_graph(
            graph, e9_root, symbols, changed_files
        )
        warnings.extend(graph_warnings)
        endpoints = _merge_endpoints(endpoints, extra_endpoints)
        _trace_end(trace, revision, graph_span)
    else:
        warnings.append("已跳过外部 MCP 查询（--skip-mcp）")

    if not pure_frontend:
        facts_mod.finalize_endpoint_diagnostics(endpoint_diag, endpoints, changed_files)
        if endpoint_diag["needs_manual_review"]:
            warnings.append(
                "端点提取为空：endpoint_diagnostics 已给出候选入口，需人工复核（不静默跳过）"
            )

    inventory = inventory_mod.build_inventory(api_test)
    existing_api = inventory_mod.match_existing(
        endpoints,
        inventory,
        db_path=inventory_mod.index_db_path(api_test),
    )
    if not skip_mcp and not pure_frontend:
        try:
            from skill_utils.api_index_db import load_test_methods

            test_coverage = coverage_mod.callers_coverage(
                graph,
                api_test,
                symbols,
                load_test_methods(inventory_mod.index_db_path(api_test)),
            )
        except Exception as exc:
            warnings.append(f"MCP callers 覆盖查询失败（外部 MCP 不可用时降级跳过）: {exc}")

    payload = {
        "revision": revision,
        "author": log_info.get("author") or "",
        "date": log_info.get("date") or "",
        "message": log_info.get("message") or "",
        "working_copy_revision": working_rev,
        "changed_files": changed_files,
        "symbols": symbols,
        "endpoints": endpoints,
        "endpoint_diagnostics": endpoint_diag,
        "impact": impact_rows,
        "existing_api": existing_api,
        "test_coverage": test_coverage,
        "diff_excerpt": facts_mod.diff_excerpt(diff_text),
        "warnings": warnings,
        "confidence": "medium",
        "pure_frontend": pure_frontend,
    }
    payload["confidence"] = facts_mod.compute_confidence(warnings, endpoints, changed_files)

    lookup_graph = None if (skip_mcp or pure_frontend) else graph
    lookup_span = _trace_begin(trace, revision, "reverse_lookup", "build_evidence")
    reverse_payload = reverse_lookup_mod.build_reverse_lookup(root, payload, graph=lookup_graph)
    payload["frontend_operations"] = list(reverse_payload.get("frontend_operations") or [])
    _trace_end(trace, revision, lookup_span)

    paths_out = report_mod.write_outputs(out_dir, payload)
    paths_out["reverse_lookup"] = reverse_lookup_mod.write_reverse_lookup(out_dir, reverse_payload)
    revision_meta.record_revision_meta(
        inventory_mod.index_db_path(api_test),
        revision,
        log_info,
        paths_out["html"],
    )
    inventory_mod.write_inventory(api_test, out_base / "_inventory.json")

    missing_key_facts = _collect_missing_key_facts(payload)
    status = "blocked" if missing_key_facts else "complete"

    return {
        "revision": revision,
        "mark": mark,
        "status": status,
        "out_dir": out_dir,
        "paths": paths_out,
        "facts": payload,
        "attempts": 1,
        "missing_key_facts": missing_key_facts,
    }