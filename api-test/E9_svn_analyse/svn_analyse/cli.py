# -*- coding: utf-8 -*-
"""svn_analyse 命令行：analyse / inventory / render / retest / select / check-consistency。

路径约定：
- 分析产物默认落在 E9_svn_analyse/output/（不入 Git）。
- 所有代码分析统一走外部 MCP（codebase-memory），不执行本地 SVN 操作。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from svn_analyse import coverage as coverage_mod, facts as facts_mod, inventory as inventory_mod, paths, revision_meta
from svn_analyse import mcp_client
from svn_analyse import report as report_mod
from svn_analyse import reverse_lookup as reverse_lookup_mod
from svn_analyse.revision import RevisionParseError, parse_revision, revision_mark
from svn_analyse import select as select_mod
from svn_analyse import analysis_worker
from svn_analyse import revision_set, batch_orchestrator

paths.ensure_framework_importable()


def repo_root_from_here() -> Path:
    """默认仓库根：工作区根目录。"""
    return paths.repo_root()


def _trace_adapter() -> Any:
    """四期 T4.6：加载阶段 Trace 采集适配器；不可用时静默返回 None。

    设置环境变量 ``E9_TRACE=0`` 可关闭采集（默认开启，产物落 runtime/trace）。
    """
    if os.environ.get("E9_TRACE", "1").strip().lower() in {"0", "off", "false"}:
        return None
    try:
        paths.ensure_framework_importable()
        from tools import phase_trace as trace_mod

        return trace_mod
    except Exception:  # noqa: BLE001 — 可观测性缺失不阻断分析
        return None


def _trace_begin(trace: Any, revision: int, phase: str, step: str) -> str | None:
    if trace is None:
        return None
    try:
        return trace.begin_span(revision, phase, step)
    except Exception:  # noqa: BLE001
        return None


def _trace_end(trace: Any, revision: int, span_id: str | None, status: str = "ok", error_type: str = "") -> None:
    if trace is None or not span_id:
        return
    try:
        trace.end_span(revision, span_id, status=status, error_type=error_type)
    except Exception:  # noqa: BLE001 — Trace 失败不影响主流程
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E9 提交影响分析")
    parser.add_argument("--root", default=None, help="仓库根目录")
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyse = sub.add_parser("analyse", help="阶段 A：通过 MCP 查询变更、采事实、写报告骨架")
    analyse.add_argument("revision", help="r349084 / Revision r349084 / 349084")
    analyse.add_argument("--api-test-E9", default="api-test-E9")
    analyse.add_argument("--output", default=None, help="分析产物目录，默认 E9_svn_analyse/output/")
    analyse.add_argument("--skip-mcp", action="store_true")

    inv = sub.add_parser("inventory", help="扫描 api-test-E9 已有 URL / 方法 / 用例")
    inv.add_argument("--api-test-E9", default="api-test-E9")
    inv.add_argument("--refresh-index", action="store_true", help="强制全量重建 page_api SQLite 索引")

    select = sub.add_parser("select", help="按功能关键词或 revision 选取关联用例")
    group = select.add_mutually_exclusive_group(required=True)
    group.add_argument("--keyword", help="提交说明或功能关键词")
    group.add_argument("--revision", help="单个 revision，例如 r349094")
    select.add_argument("--api-test-E9", default="api-test-E9")

    consistency = sub.add_parser("check-consistency", help="比较 revision mark 与 MCP callers")
    consistency.add_argument("--revision", required=True)
    consistency.add_argument("--api-test-E9", default="api-test-E9")
    consistency.add_argument("--project", default="api-test-E9")

    render = sub.add_parser("render", help="根据 facts.json + design.json 重生成 HTML/MD")
    render.add_argument("out_dir", help="例如 E9_svn_analyse/output/r349084")

    reverse = sub.add_parser(
        "reverse-lookup", help="四期 T4.2：生成/重建反查证据包 reverse_lookup.json"
    )
    reverse.add_argument("revision", help="r349155 / 349155")
    reverse.add_argument("--symbol", default=None, help="只输出指定符号的反查块")
    reverse.add_argument("--skip-mcp", action="store_true", help="跳过 MCP callers，仅静态反查")
    reverse.add_argument("--output", default=None, help="分析产物目录，默认 E9_svn_analyse/output/")

    retest = sub.add_parser("retest", help="阶段 C：按 pytest mark 执行并出 Allure")
    retest.add_argument("revision")
    retest.add_argument("--api-test-E9", default="api-test-E9")

    batch = sub.add_parser("batch", help="五期：批次分析（连续区间或显式集合）")
    batch.add_argument("text", help="用户输入文本，例如：分析 Revision r349181 到 Revision r349184，提交说明：...")
    batch.add_argument("--api-test-E9", default="api-test-E9")
    batch.add_argument("--output", default=None, help="分析产物目录，默认 E9_svn_analyse/output/")
    batch.add_argument("--skip-mcp", action="store_true", help="跳过 MCP 图谱查询")
    return parser


def _resolve_output_root(raw: str | None) -> Path:
    """相对路径按 E9_svn_analyse/ 解析；缺省返回 E9_svn_analyse/output。"""
    if not raw:
        return paths.output_root()
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return paths.ANALYSE_ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else repo_root_from_here()

    try:
        if args.cmd == "analyse":
            result = run_analyse(
                args.revision,
                root=root,
                api_test_rel=args.api_test_E9,
                output_root=_resolve_output_root(args.output),
                skip_mcp=args.skip_mcp,
            )
            _print_analyse_result(result)
            return 0
        if args.cmd == "inventory":
            api_test = root / args.api_test_E9
            dest = paths.output_root() / "_inventory.json"
            inventory_mod.write_inventory(api_test, dest, refresh_index=args.refresh_index)
            print(dest)
            return 0
        if args.cmd == "select":
            api_test = root / args.api_test_E9
            inventory_mod.build_inventory(api_test)
            database = inventory_mod.index_db_path(api_test)
            if args.keyword:
                rows = select_mod.select_by_keyword(database, args.keyword)
            else:
                rows = select_mod.select_by_revision(database, parse_revision(args.revision))
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "check-consistency":
            api_test = root / args.api_test_E9
            inventory = inventory_mod.build_inventory(api_test)
            revision = revision_mark(parse_revision(args.revision))
            marked_records = [
                item
                for item in inventory.get("tests", [])
                if revision in (item.get("marks") or [])
            ]
            facts = _load_revision_facts(revision)
            symbols, symbol_basis = coverage_mod.select_consistency_symbols(
                facts,
                inventory.get("wrappers", []),
                marked_records,
            )
            caller_rows = coverage_mod.callers_coverage(
                mcp_client,
                root / args.project,
                [{"name": symbol} for symbol in symbols],
                inventory.get("tests", []),
            )
            callers = [name for row in caller_rows for name in row.get("covered_tests", [])]
            payload = coverage_mod.check_consistency(
                [item["name"] for item in marked_records],
                callers,
            )
            payload.update(
                {
                    "revision": revision,
                    "symbols": symbols,
                    "symbol_basis": symbol_basis,
                    "caller_rows": caller_rows,
                }
            )
            if not symbols:
                payload["explanation"] = "未找到可映射到 api-test-E9 图的变更符号，无法做 callers 一致性判定"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "render":
            out_dir = Path(args.out_dir)
            if not out_dir.is_absolute():
                out_dir = paths.ANALYSE_ROOT / out_dir
            render_paths = report_mod.render_from_dir(out_dir)
            print(render_paths["html"])
            return 0
        if args.cmd == "reverse-lookup":
            return run_reverse_lookup(
                args.revision,
                root=root,
                output_root=_resolve_output_root(args.output),
                symbol=args.symbol,
                skip_mcp=args.skip_mcp,
            )
        if args.cmd == "retest":
            revision = parse_revision(args.revision)
            return run_retest(revision, root / args.api_test_E9)
        if args.cmd == "batch":
            return run_batch_analyse(
                args.text,
                root=root,
                api_test_rel=args.api_test_E9,
                output_root=_resolve_output_root(args.output),
                skip_mcp=args.skip_mcp,
            )
    except RevisionParseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


def run_analyse(
    revision_text: str,
    root: Path,
    api_test_rel: str = "api-test-E9",
    output_root: str | Path | None = None,
    skip_mcp: bool = False,
    skip_update: bool = False,
    graph: Any = mcp_client,
    ops: Any = None,
    svn: Any = None,
) -> dict[str, Any]:
    """阶段 A 入口：记录 stage_a trace span，失败时登记错误类型后原样抛出。

    ``skip_update`` 已无效果（查询不会 svn update），仅为兼容旧测试签名而保留。
    ``svn`` 仅测试替身兼容；生产路径走 ``ops.svn_log`` / ``ops.svn_diff``。
    """
    del skip_update
    revision = parse_revision(revision_text)
    trace = _trace_adapter()
    root_span = _trace_begin(trace, revision, "stage_a", "analyse")
    try:
        result = _run_analyse_inner(
            revision_text,
            root=root,
            api_test_rel=api_test_rel,
            output_root=output_root,
            skip_mcp=skip_mcp,
            graph=graph,
            ops=ops,
            svn=svn,
            trace=trace,
        )
    except Exception as exc:  # noqa: BLE001 — 仅为 trace 留痕，异常原样上抛
        _trace_end(trace, revision, root_span, status="failed", error_type=type(exc).__name__)
        raise
    _trace_end(trace, revision, root_span)
    return result


def _run_analyse_inner(
    revision_text: str,
    root: Path,
    api_test_rel: str = "api-test-E9",
    output_root: str | Path | None = None,
    skip_mcp: bool = False,
    graph: Any = mcp_client,
    ops: Any = None,
    svn: Any = None,
    trace: Any = None,
) -> dict[str, Any]:
    """委托 analysis_worker 执行单笔分析（五期：抽取公共 worker）。"""
    revision = parse_revision(revision_text)
    ops_client = ops if ops is not None else (_SvnOpsAdapter(svn) if svn is not None else graph)
    result = analysis_worker.analyze_single_revision(
        revision=revision,
        root=root,
        api_test_rel=api_test_rel,
        output_root=output_root,
        skip_mcp=skip_mcp,
        graph=graph,
        ops=ops_client,
        trace=trace,
    )
    return {
        "revision": result["revision"],
        "mark": result["mark"],
        "out_dir": result["out_dir"],
        "paths": result["paths"],
        "facts": result["facts"],
    }


def run_retest(
    revision: int,
    api_test_dir: Path,
    runner: Callable[..., int] | None = None,
) -> int:
    """封装 ``python runpytest.py -m r<rev> --clean``。"""
    mark = revision_mark(revision)
    if runner is None:
        import subprocess

        def runner(command, cwd):  # type: ignore[misc]：兼容动态注入的执行函数签名
            completed = subprocess.run(command, cwd=str(cwd), check=False)
            return int(completed.returncode)

    command = [sys.executable, "runpytest.py", "-m", mark, "--clean"]
    return int(runner(command, api_test_dir))


def run_batch_analyse(
    text: str,
    root: Path,
    api_test_rel: str = "api-test-E9",
    output_root: str | Path | None = None,
    skip_mcp: bool = False,
    graph: Any = mcp_client,
) -> int:
    """五期：批次分析入口。

    解析输入 → resolver → 逐 revision 分析 → 聚合 → 写入产物。
    返回 0 表示成功，非 0 表示阻断。
    """
    # 1. 解析输入
    parsed = revision_set.parse_batch_input(text)
    if not parsed["valid"]:
        print(f"ERROR: {parsed.get('error')}", file=sys.stderr)
        return 2

    mode = parsed["mode"]
    batch_message = parsed["batch_message"]
    out_base = Path(output_root) if output_root else paths.output_root()

    # 2. Resolver：解析实际 revision 集合
    if mode == "range":
        from_rev = parsed.get("from_rev")
        to_rev = parsed.get("to_rev")
        if not skip_mcp and from_rev is not None and to_rev is not None:
            # 闭区间跨度 ≤ 10，优先使用一次区间查询（方案二）
            range_result = mcp_client.list_revisions_in_range(from_rev, to_rev)
            if range_result.get("ok") and range_result.get("complete"):
                # 直接使用区间查询结果
                revs = [item["revision"] for item in range_result.get("revisions") or []]
                resolution = {
                    "schema_version": 1,
                    "mode": "range",
                    "input_order": [from_rev, to_rev],
                    "analysis_order": revs,
                    "resolved_revisions": revs,
                    "skipped_revisions": [],
                    "complete": True,
                    "source": "e9-ops",
                    "source_queries": [{"type": "list_revisions_in_range", "from": from_rev, "to": to_rev}],
                    "boundary_evidence": range_result.get("boundary") or {},
                    "error": None,
                    "status": "accepted",
                }
            else:
                # 降级到邻域查询
                resolver = mcp_client.list_revisions
                resolution = revision_set.resolve_revision_set(
                    resolver=resolver,
                    mode=mode,
                    from_rev=from_rev,
                    to_rev=to_rev,
                )
        else:
            resolution = revision_set.resolve_revision_set(
                resolver=None,
                mode=mode,
                from_rev=from_rev,
                to_rev=to_rev,
            )
    else:
        resolution = revision_set.resolve_revision_set(
            resolver=None,
            mode=mode,
            input_order=parsed.get("input_order"),
        )

    if not resolution["complete"]:
        print(f"ERROR: resolver 阻断 — {resolution.get('error')}", file=sys.stderr)
        print(json.dumps(resolution, ensure_ascii=False, indent=2))
        return 2

    analysis_order = resolution["analysis_order"]
    if len(analysis_order) < 2:
        print(f"ERROR: 仅解析到 {len(analysis_order)} 笔 revision，请使用单笔模板", file=sys.stderr)
        return 2

    # 3. 校验
    errors = revision_set.validate_batch(
        mode=mode,
        revisions=analysis_order,
        batch_message=batch_message,
        from_rev=parsed.get("from_rev"),
        to_rev=parsed.get("to_rev"),
    )
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # 4. 生成 batch_id
    batch_id = revision_set.generate_batch_id(analysis_order)

    # 5. 运行批次分析
    api_test = root / api_test_rel
    result = batch_orchestrator.run_batch(
        worker=analysis_worker.analyze_single_revision,
        analysis_order=analysis_order,
        batch_message=batch_message,
        batch_id=batch_id,
        output_root=out_base,
        root=root,
        api_test_rel=api_test_rel,
        skip_mcp=skip_mcp,
        graph=graph,
    )

    _print_batch_result(result)
    return 0


def _print_batch_result(result: dict[str, Any]) -> None:
    """打印批次分析结果摘要。"""
    batch_dir = result["batch_dir"]
    print(json.dumps(
        {
            "batch_id": result["batch_id"],
            "batch_status": result["batch_status"],
            "stage_b_gate": result["stage_b_gate"],
            "batch_dir": str(batch_dir),
            "revisions": [
                {
                    "revision": r["revision"],
                    "status": r["status"],
                    "attempts": r.get("attempts", 0),
                }
                for r in result["revision_results"]
            ],
            "aggregate_design": str(batch_dir / "design.json"),
            "eligible_for_stage_b": result["aggregate_design"].get("eligible_for_stage_b"),
        },
        ensure_ascii=False,
        indent=2,
    )) if result["stage_b_gate"] else print(
        f"批次 {result['batch_id']} 状态={result['batch_status']}，stage_b_gate=False，"
        f"不进入阶段 B。产物: {batch_dir}"
    )


def run_reverse_lookup(
    revision_text: str,
    root: Path,
    output_root: str | Path | None = None,
    symbol: str | None = None,
    skip_mcp: bool = False,
    graph: Any = mcp_client,
) -> int:
    """四期 T4.2：重建指定 revision 的 reverse_lookup.json，或查询单符号块。

    依赖阶段 A 已产出的 facts.json；缺失时报错退出，不伪造证据。
    """
    revision = parse_revision(revision_text)
    mark = revision_mark(revision)
    out_base = Path(output_root) if output_root else paths.output_root()
    out_dir = out_base / mark
    facts_path = out_dir / "facts.json"
    if not facts_path.is_file():
        print(f"ERROR: 缺少 {facts_path}，请先执行 analyse {mark}", file=sys.stderr)
        return 2
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    lookup_graph = None if (skip_mcp or facts.get("pure_frontend")) else graph
    payload = reverse_lookup_mod.build_reverse_lookup(root, facts, graph=lookup_graph)
    dest = reverse_lookup_mod.write_reverse_lookup(out_dir, payload)
    if symbol:
        block = next(
            (item for item in payload.get("symbols") or [] if item.get("name") == symbol),
            None,
        )
        if block is None:
            print(f"ERROR: 反查证据包中没有符号 {symbol}", file=sys.stderr)
            return 2
        print(json.dumps(block, ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "revision": revision,
                "reverse_lookup": str(dest),
                "entries": len(payload.get("entries") or []),
                "contracts": len(payload.get("contracts") or []),
                "frontend_operations": len(payload.get("frontend_operations") or []),
                "frontend_misses": len((payload.get("frontend_scan") or {}).get("misses") or []),
                "uncovered_endpoints": (payload.get("coverage_consistency") or {}).get(
                    "uncovered_endpoints"
                )
                or [],
                "degraded": payload.get("degraded") or {},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


class _SvnOpsAdapter:
    """把旧测试替身 FakeSvn 适配成 e9_svn_log / e9_svn_diff 返回值。生产路径不使用。"""

    def __init__(self, svn: Any) -> None:
        self._svn = svn

    def svn_log(self, revision: int) -> dict[str, Any]:
        parsed = self._svn.parse_log_xml(self._svn.log_xml(None, revision))
        return {
            "ok": True,
            "revision": parsed.get("revision") or revision,
            "author": parsed.get("author") or "",
            "date": parsed.get("date") or "",
            "message": parsed.get("message") or "",
            "paths": list(parsed.get("paths") or []),
            "working_copy_revision": str(self._svn.working_copy_revision(None) or ""),
        }

    def svn_diff(self, revision: int, max_bytes: int = 262144) -> dict[str, Any]:
        text = self._svn.diff(None, revision)
        raw = text.encode("utf-8", errors="replace")
        truncated = len(raw) > max_bytes
        if truncated:
            text = raw[:max_bytes].decode("utf-8", errors="replace") + "\n... (truncated)"
        return {
            "ok": True,
            "revision": revision,
            "diff": text,
            "truncated": truncated,
            "byte_length": min(len(raw), max_bytes),
            "changed_paths": facts_mod.parse_diff_files(text),
        }


def _fetch_temporal(ops: Any, revision: int) -> tuple[dict[str, Any], str, str, list[str]]:
    """从运维 MCP（或测试替身）取 log / diff；失败写入警告，不编造变更。"""
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
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"MCP e9_svn_log 失败: {exc}")
    try:
        diff_payload = ops.svn_diff(revision)
        diff_text = str(diff_payload.get("diff") or "")
        if diff_payload.get("truncated"):
            warnings.append("e9_svn_diff 返回已截断")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"MCP e9_svn_diff 失败: {exc}")
    return log_info, diff_text, working_rev, warnings


def _changed_files(log_paths: list[dict[str, str]], diff_text: str, repo: Path) -> list[dict[str, str]]:
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
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"mcp callers {query} 失败: {exc}")
            size = graph.parse_impact_size(impact_text)
            changed_this = query in changed_names or any(
                query in (item.get("name") or "") for item in symbols
            )
            note = "本次命中" if changed_this else "关联符号"
            # 公共方法：若变更文件里没有该方法的定义文件，标不扩散
            defined_here = any(
                Path(item["path"]).stem == query for item in changed_files
            )
            if not defined_here and size:
                note = "本体未改，不扩散"
            impact_rows.append({"symbol": query, "size": size, "note": note})
            refs = graph.extract_action_refs((impact_text or "") + "\n" + (callers_text or ""))
            graph_endpoints = facts_mod.endpoints_from_action_refs(repo, refs)
            for item in graph_endpoints:
                # via 保留具体解析策略；另记触发来源，便于证据追溯（四期 T4.1）
                item.setdefault("prompted_by", facts_mod.VIA_MCP)
            extra.extend(graph_endpoints)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"mcp impact {query} 失败: {exc}")
    return impact_rows, extra, warnings


def _merge_endpoints(
    left: list[dict[str, str]],
    right: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, str]] = []
    for item in left + right:
        key = (item.get("method") or "", item.get("url") or "", item.get("action") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _load_revision_facts(revision: str) -> dict[str, Any]:
    """读取阶段 A 已生成的事实；缺失时返回空结构以便输出明确限制。"""
    path = paths.output_root() / revision / "facts.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _print_analyse_result(result: dict[str, Any]) -> None:
    result_paths = result["paths"]
    print(json.dumps(
        {
            "revision": result["revision"],
            "mark": result["mark"],
            "out_dir": str(result["out_dir"]),
            "facts": str(result_paths["facts"]),
            "design": str(result_paths["design"]),
            "reverse_lookup": str(result_paths.get("reverse_lookup") or ""),
            "html": str(result_paths["html"]),
            "md": str(result_paths["md"]),
            "confidence": result["facts"].get("confidence"),
            "pure_frontend": result["facts"].get("pure_frontend"),
            "warnings": result["facts"].get("warnings"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
