# -*- coding: utf-8 -*-
"""五期：批次编排器 —— 逐 revision 调度、重试、聚合与门禁。

本模块不复制 ``_run_analyse_inner`` 的查询和事实逻辑，只负责：
- 逐 revision 调用 ``analysis_worker.analyze_single_revision()``（最多 3 次 attempt）
- 聚合逐笔 facts/design 为 batch 级产物
- 生成 ``aggregate_design``
- 校验阶段 B 门禁
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from svn_analyse import report as report_mod
from svn_analyse import reverse_lookup as reverse_lookup_mod
from svn_analyse import facts as facts_mod
from svn_analyse.revision import revision_mark
from svn_analyse import revision_set


# ── 逐 revision attempt ───────────────────────────────────────────


def _attempt_single_revision(
    worker: Callable,
    revision: int,
    max_attempts: int = 3,
    **worker_kwargs,
) -> dict[str, Any]:
    """对单个 revision 执行最多 ``max_attempts`` 次分析尝试。

    每次 attempt 记录阶段、错误类型和建议。成功不重复，失败保留 error 和
    attempt_log。返回的 dict 与 ``analyze_single_revision`` 兼容，额外增加
    ``attempts``、``attempt_log``、``error`` 字段。
    """
    attempt_log: list[dict[str, Any]] = []
    last_error: str | None = None

    for attempt_num in range(1, max_attempts + 1):
        try:
            result = worker(revision=revision, **worker_kwargs)
            result["attempts"] = attempt_num
            result["attempt_log"] = attempt_log
            result["error"] = None
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            error_msg = str(exc)
            attempt_log.append({
                "attempt": attempt_num,
                "status": "failed",
                "error_type": error_type,
                "error": error_msg,
                "phase": "stage_a",
            })
            last_error = f"{error_type}: {error_msg}"

    # 全部失败
    return {
        "revision": revision,
        "mark": revision_mark(revision),
        "status": "blocked",
        "out_dir": worker_kwargs.get("output_root", Path(".")) / revision_mark(revision),
        "paths": {},
        "facts": {
            "revision": revision,
            "author": "",
            "date": "",
            "message": "",
            "changed_files": [],
            "symbols": [],
            "endpoints": [],
            "impact": [],
            "existing_api": [],
            "test_coverage": [],
            "diff_excerpt": "",
            "warnings": [f"全部 {max_attempts} 次 attempt 失败"],
            "confidence": "low",
            "pure_frontend": False,
            "endpoint_diagnostics": {"needs_manual_review": True, "skipped": None},
            "frontend_operations": [],
        },
        "attempts": max_attempts,
        "attempt_log": attempt_log,
        "missing_key_facts": ["全部 attempt 失败"],
        "error": last_error,
    }


# ── 批次主入口 ────────────────────────────────────────────────────


def run_batch(
    worker: Callable,
    analysis_order: list[int],
    batch_message: str,
    batch_id: str,
    output_root: Path,
    root: Path,
    api_test_rel: str = "api-test-E9",
    **worker_kwargs,
) -> dict[str, Any]:
    """批次分析主入口：逐 revision 调度 → 聚合 → 写入产物。

    Args:
        worker: 单 revision 分析函数，签名 ``worker(revision, **kwargs) -> dict``
        analysis_order: 升序排列的 revision 列表
        batch_message: 批次总结说明
        batch_id: 批次标识
        output_root: 产物根目录（产在 ``output_root/batch_<id>/``）
        root: 工作区根目录
        api_test_rel: 接口测试目录相对路径

    Returns:
        dict with ``batch_status``, ``stage_b_gate``, ``revision_results``,
        ``aggregated_facts``, ``aggregate_design``, ``batch_dir``
    """
    batch_dir = output_root / batch_id
    revisions_dir = batch_dir / "revisions"
    revisions_dir.mkdir(parents=True, exist_ok=True)

    # 逐 revision 分析
    revision_results: list[dict[str, Any]] = []
    for rev in analysis_order:
        rev_output = revisions_dir / revision_mark(rev)
        rev_output.mkdir(parents=True, exist_ok=True)
        result = _attempt_single_revision(
            worker=worker,
            revision=rev,
            max_attempts=3,
            root=root,
            api_test_rel=api_test_rel,
            output_root=rev_output,
            **worker_kwargs,
        )
        revision_results.append(result)

    # 判定批次状态
    all_complete = all(r["status"] == "complete" for r in revision_results)
    batch_status = "complete" if all_complete else "blocked"

    # 聚合
    aggregated_facts = _aggregate_facts(revision_results)
    aggregated_facts["batch_id"] = batch_id
    aggregated_facts["batch_message"] = batch_message
    aggregated_facts["batch_status"] = batch_status
    aggregated_facts["analysis_run_id"] = revision_set.generate_analysis_run_id(batch_id)

    # 将逐笔 design 写入 revision_designs
    revision_designs = []
    for result in revision_results:
        if result["status"] == "complete":
            design = report_mod.design_skeleton(result["facts"])
            revision_designs.append(design)
    aggregated_facts["revision_designs"] = revision_designs

    # 生成 aggregate_design
    aggregate_design = _aggregate_design_skeleton(aggregated_facts, batch_id)

    # 阶段 B 门禁
    stage_b_gate = all_complete and aggregate_design["eligible_for_stage_b"]

    # 写入批次产物
    report_mod.write_json(batch_dir / "facts.json", aggregated_facts)
    report_mod.write_json(batch_dir / "design.json", aggregate_design)

    # 写入逐笔产物到子目录
    for result in revision_results:
        if result["status"] == "complete":
            rev_dir = revisions_dir / result["mark"]
            report_mod.write_json(rev_dir / "facts.json", result["facts"])
            report_mod.write_json(rev_dir / "design.json", report_mod.design_skeleton(result["facts"]))

    return {
        "batch_id": batch_id,
        "batch_status": batch_status,
        "stage_b_gate": stage_b_gate,
        "revision_results": revision_results,
        "aggregated_facts": aggregated_facts,
        "aggregate_design": aggregate_design,
        "batch_dir": batch_dir,
    }


# ── 聚合 ──────────────────────────────────────────────────────────


def _aggregate_facts(revision_results: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合逐笔 facts：去重合并文件、符号、端点、影响模块和用例候选。

    保留 ``source_revisions`` 追踪每条结论的来源。
    """
    resolved_revisions: list[int] = []
    affected_files: dict[str, dict[str, Any]] = {}
    affected_modules: set[str] = set()
    endpoints: dict[str, dict[str, Any]] = {}
    symbols: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    cross_commit_summary: list[str] = []
    revision_details: list[dict[str, Any]] = []

    for result in revision_results:
        rev = result["revision"]
        resolved_revisions.append(rev)
        facts = result.get("facts") or {}
        status = result["status"]
        attempts = result.get("attempts", 0)

        revision_details.append({
            "revision": rev,
            "status": status,
            "attempts": attempts,
            "author": facts.get("author") or "",
            "message": facts.get("message") or "",
            "missing_key_facts": result.get("missing_key_facts") or [],
        })

        if status != "complete":
            warnings.append(f"r{rev} 状态={status}（attempts={attempts}）")
            continue

        # 合并文件
        for f in facts.get("changed_files") or []:
            path = f.get("path") or ""
            if path not in affected_files:
                affected_files[path] = {
                    "path": path,
                    "source_revisions": [rev],
                    "actions": [f.get("action") or ""],
                    "kind": f.get("kind") or "",
                    "change_layer": f.get("change_layer") or "",
                }
            else:
                if rev not in affected_files[path]["source_revisions"]:
                    affected_files[path]["source_revisions"].append(rev)
                if f.get("action") not in affected_files[path]["actions"]:
                    affected_files[path]["actions"].append(f.get("action") or "")

        # 合并符号
        for s in facts.get("symbols") or []:
            name = s.get("name") or ""
            if name not in symbols:
                symbols[name] = {
                    "name": name,
                    "kind": s.get("kind") or "",
                    "source_revisions": [rev],
                }
            else:
                if rev not in symbols[name]["source_revisions"]:
                    symbols[name]["source_revisions"].append(rev)

        # 合并端点
        for ep in facts.get("endpoints") or []:
            key = f"{ep.get('method')}|{ep.get('url')}|{ep.get('action')}"
            if key not in endpoints:
                endpoints[key] = {
                    "method": ep.get("method") or "",
                    "url": ep.get("url") or "",
                    "action": ep.get("action") or "",
                    "via": ep.get("via") or "",
                    "source_file": ep.get("source_file") or "",
                    "source_revisions": [rev],
                }
            else:
                if rev not in endpoints[key]["source_revisions"]:
                    endpoints[key]["source_revisions"].append(rev)

        # 提取模块
        for f in facts.get("changed_files") or []:
            path = f.get("path") or ""
            parts = path.split("/")
            if len(parts) >= 2:
                # 提取模块名：src/com/api/<module> → <module>
                if "src" in parts:
                    src_idx = parts.index("src")
                    if len(parts) > src_idx + 3:
                        affected_modules.add(parts[src_idx + 3])  # com/api/<模块名>
                # 其他顶层目录（如 wui、workflow 等）
                if parts[0] not in ("src", "WEB-INF", "classbean"):
                    affected_modules.add(parts[0])
            # 短路径：直接用最后一层目录作为模块
            if len(parts) >= 2:
                module_dir = parts[-2]  # 文件所在目录
                if module_dir not in ("src", "WEB-INF", "classbean", "com", "api", "engine"):
                    affected_modules.add(module_dir)

    # 跨提交总结
    if len(resolved_revisions) > 1:
        cross_commit_summary.append(
            f"批次包含 {len(resolved_revisions)} 笔提交，"
            f"涉及 {len(affected_files)} 个文件、{len(endpoints)} 个端点"
        )

    return {
        "schema_version": 1,
        "analysis_type": "batch",
        "resolved_revisions": resolved_revisions,
        "revisions": revision_details,
        "affected_files": sorted(affected_files.values(), key=lambda x: x["path"]),
        "affected_modules": sorted(affected_modules),
        "endpoints": sorted(endpoints.values(), key=lambda x: f"{x['method']}|{x['url']}"),
        "symbols": sorted(symbols.values(), key=lambda x: x["name"]),
        "warnings": warnings,
        "cross_commit_summary": cross_commit_summary,
        "revision_designs": [],
    }


def _aggregate_design_skeleton(
    aggregated_facts: dict[str, Any],
    batch_id: str,
) -> dict[str, Any]:
    """生成批次 aggregate_design 骨架。

    包含逐 revision marks、联合 api_cases、eligible_for_stage_b 等字段。
    """
    resolved = aggregated_facts.get("resolved_revisions") or []
    marks = [revision_mark(r) for r in resolved]
    batch_status = aggregated_facts.get("batch_status", "complete")

    # 合并 api_cases
    api_cases: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for ep in aggregated_facts.get("endpoints") or []:
        url = ep.get("url") or ""
        method = ep.get("method") or ""
        key = f"{method}|{url}"
        if key in seen_urls:
            continue
        seen_urls.add(key)
        api_cases.append({
            "url": url,
            "http_method": method,
            "action": ep.get("action") or "",
            "revision_marks": marks,
            "suggested_wrapper": "",
            "suggested_test": "",
            "scenarios": ["正常场景", "边界场景", "异常场景"],
            "source_revisions": ep.get("source_revisions") or [],
        })

    eligible = batch_status == "complete" and len(resolved) >= 2

    return {
        "batch_id": batch_id,
        "analysis_type": "batch",
        "title": f"批次 {batch_id} 联合影响分析",
        "behavior_change": "",
        "impact_summary": "",
        "revision_marks": marks,
        "revision_designs": aggregated_facts.get("revision_designs") or [],
        "api_cases": api_cases,
        "functional_cases": [],
        "risks": aggregated_facts.get("warnings") or [],
        "env_assumption": report_mod.DEFAULT_ENV_ASSUMPTION,
        "next_command": "按方案实现接口自动化",
        "confidence": "medium",
        "eligible_for_stage_b": eligible,
        "source_revisions": resolved,
        "cross_commit_summary": aggregated_facts.get("cross_commit_summary") or [],
    }


# ── 阶段 B 门禁 ───────────────────────────────────────────────────


def _check_batch_gate(
    batch_status: str,
    stage_b_gate: bool,
    eligible_for_stage_b: bool,
) -> dict[str, Any]:
    """校验批次阶段 B 门禁，返回逐项检查结果。

    三项全部通过才能进入阶段 B。
    """
    checks = {
        "batch_complete": batch_status == "complete",
        "gate": stage_b_gate,
        "eligible": eligible_for_stage_b,
    }
    all_pass = all(checks.values())
    reasons: list[str] = []
    if not checks["batch_complete"]:
        reasons.append("批次状态不是 complete")
    if not checks["gate"]:
        reasons.append("stage_b_gate 未通过")
    if not checks["eligible"]:
        reasons.append("aggregate_design 标记为不可进入阶段 B")

    return {
        "pass": all_pass,
        "checks": checks,
        "reasons": reasons,
    }


# ── 阶段 B：批次用例生成 ──────────────────────────────────────────


def generate_batch_test_case(
    aggregate_design: dict[str, Any],
    module_name: str,
    test_name: str,
    description: str = "",
) -> str:
    """从 aggregate_design 生成单个批次接口用例的 Python 代码骨架。

    返回完整的 pytest 测试函数字符串，包含：
    - 全部 revision mark 装饰器
    - docstring（含功能用例编号引用）
    - 测试函数骨架

    Args:
        aggregate_design: 批次 aggregate_design
        module_name: 模块名（如 ``workflow``）
        test_name: 测试函数名（如 ``test_batch_force_over``）
        description: 用例描述（写入 docstring）
    """
    marks = [f"@pytest.mark.r{rev}" for rev in sorted(aggregate_design.get("source_revisions") or [])]
    batch_id = aggregate_design.get("batch_id", "")
    marks_str = "\n".join(marks)
    desc = description or f"批次 {batch_id} 接口回归用例"

    return f'''{marks_str}
def {test_name}(base_url):
    """{desc}

    批次: {batch_id}
    关联 revision: {", ".join(f"r{{rev}}" for rev in sorted(aggregate_design.get("source_revisions") or []))}
    """
    # TODO: 实现接口调用与断言
    pass
'''


def generate_batch_test_module(
    aggregate_design: dict[str, Any],
    module_name: str,
    test_cases: list[dict[str, str]],
) -> str:
    """生成完整的批次测试模块代码。

    Args:
        aggregate_design: 批次 aggregate_design
        module_name: 模块名
        test_cases: 用例列表，每项 ``{"name": str, "description": str}``

    Returns:
        完整的 .py 模块代码字符串
    """
    batch_id = aggregate_design.get("batch_id", "")
    marks = aggregate_design.get("revision_marks") or []
    marks_comment = ", ".join(marks)

    lines = [
        '# -*- coding: utf-8 -*-',
        f'"""{module_name} 模块批次接口回归用例。',
        '',
        f'批次: {batch_id}',
        f'关联 revision: {marks_comment}',
        '生成方式: batch_orchestrator.generate_batch_test_module',
        '"""',
        '',
        'import pytest',
        '',
        '',
    ]

    for tc in test_cases:
        lines.append(generate_batch_test_case(
            aggregate_design=aggregate_design,
            module_name=module_name,
            test_name=tc["name"],
            description=tc.get("description", ""),
        ))
        lines.append("")

    return "\n".join(lines)


def validate_batch_ready_for_stage_b(
    batch_result: dict[str, Any],
    functional_cases_finalized: bool = False,
) -> dict[str, Any]:
    """全面校验批次是否已准备好进入阶段 B。

    校验项：
    1. batch_status == "complete"
    2. stage_b_gate == True
    3. aggregate_design.eligible_for_stage_b == True
    4. 功能用例已人工定稿（functional_cases_finalized）

    Returns:
        ``{"ready": bool, "checks": dict, "reasons": list}``
    """
    checks = {
        "batch_complete": batch_result.get("batch_status") == "complete",
        "stage_b_gate": batch_result.get("stage_b_gate", False),
        "eligible": batch_result.get("aggregate_design", {}).get("eligible_for_stage_b", False),
        "functional_cases_finalized": functional_cases_finalized,
    }
    all_ready = all(checks.values())
    reasons: list[str] = []
    if not checks["batch_complete"]:
        reasons.append("批次状态不是 complete")
    if not checks["stage_b_gate"]:
        reasons.append("stage_b_gate 未通过")
    if not checks["eligible"]:
        reasons.append("aggregate_design 标记不可进入阶段 B")
    if not checks["functional_cases_finalized"]:
        reasons.append("功能用例清单尚未人工定稿")

    return {
        "ready": all_ready,
        "checks": checks,
        "reasons": reasons,
    }