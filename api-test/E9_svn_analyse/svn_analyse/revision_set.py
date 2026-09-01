# -*- coding: utf-8 -*-
"""五期：批次 revision 集合解析、校验和 MCP resolver 适配。

单笔 revision 解析继续使用 ``revision.py``。本模块新增：
- ``parse_batch_input``：从用户自然语言中解析连续区间或显式集合
- ``validate_batch``：校验批次约束（数量、跨度、batch_message）
- ``resolve_revision_set``：通过 MCP 邻域查询解析实际 revision 集合
- ``generate_batch_id`` / ``generate_analysis_run_id``：批次标识
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

# ── 常量 ──────────────────────────────────────────────────────────

MAX_BATCH_SIZE = 10
MAX_RANGE_SPAN = 10

# 连续区间模板：匹配 "分析 Revision r349181 到 Revision r349184" 等
_RANGE_RE = re.compile(
    r"(?:分析|快速测试)\s+"
    r"(?:Revision|revision|修订)\s*[Rr]?(?P<from_rev>\d+)"
    r"\s*(?:到|至|[-~])\s*"
    r"(?:Revision|revision|修订)\s*[Rr]?(?P<to_rev>\d+)"
)

# 显式集合模板：匹配 "Revision r349181" 等
_EXPLICIT_RE = re.compile(
    r"(?:Revision|revision|修订)\s*[Rr]?(?P<rev>\d+)"
)

# batch_message 提取
_BATCH_MSG_RE = re.compile(
    r"(?:提交说明|批次说明|batch.message)[：:]\s*(?P<msg>.+?)(?:$|[。\.]\s*(?:$|分析|快速|复测|实现|审核))"
)

# 单笔匹配（用于区分"分析 r349181" 不是批次）
_SINGLE_RE = re.compile(r"(?i)(?:^|[，,\s。、])[Rr]?(?P<rev>\d+)(?:[，,\s。、]|$)", re.UNICODE)


def parse_batch_input(text: str) -> dict[str, Any]:
    """从用户自然语言中解析批次输入。

    返回 dict：
    - ``valid``: bool，是否可进入批次分析
    - ``mode``: ``"range"`` | ``"explicit"`` | ``"single"`` | ``""``
    - ``batch_message``: str，批次总结说明
    - ``error``: str，校验失败原因
    - 区间模式额外：``from_rev``, ``to_rev``
    - 显式集合额外：``input_order``, ``analysis_order``
    - ``quick_test``: bool，是否快速测试模式
    """
    raw = (text or "").strip()
    if not raw:
        return {"valid": False, "mode": "", "error": "输入为空"}

    quick_test = "快速测试" in raw

    # 提取 batch_message
    batch_message = ""
    msg_match = _BATCH_MSG_RE.search(raw)
    if msg_match:
        batch_message = msg_match.group("msg").strip()

    # 检测连续区间
    range_matches = list(_RANGE_RE.finditer(raw))
    if range_matches:
        return _parse_range_mode(range_matches, batch_message, quick_test, raw)

    # 检测显式集合
    explicit_matches = list(_EXPLICIT_RE.finditer(raw))
    if len(explicit_matches) >= 2:
        return _parse_explicit_mode(explicit_matches, batch_message, quick_test, raw)

    # 检测单笔
    single_matches = list(_SINGLE_RE.finditer(raw))
    if single_matches:
        revs = list(dict.fromkeys(int(m.group("rev")) for m in single_matches if m.group("rev")))
        if revs:
            return {
                "valid": False,
                "mode": "single",
                "error": f"仅识别到 {len(revs)} 笔 revision，请使用批次模板提供 2–10 笔 revision 和 batch_message",
                "revisions": revs,
            }

    return {"valid": False, "mode": "", "error": "无法识别 revision 信息"}


def _parse_range_mode(
    matches: list[re.Match],
    batch_message: str,
    quick_test: bool,
    raw: str,
) -> dict[str, Any]:
    from_rev = int(matches[0].group("from_rev"))
    to_rev = int(matches[0].group("to_rev"))

    if from_rev > to_rev:
        from_rev, to_rev = to_rev, from_rev

    span = to_rev - from_rev
    if span > MAX_RANGE_SPAN:
        return {
            "valid": False,
            "mode": "range",
            "error": f"区间跨度 {span} 超过 {MAX_RANGE_SPAN}，请缩小端点范围后重新提问",
            "from_rev": from_rev,
            "to_rev": to_rev,
        }

    if not batch_message:
        return {
            "valid": False,
            "mode": "range",
            "error": "缺少 batch_message（批次总结说明）。请提供提交说明，例如：提交说明：no.4996246 解决了流程导入不会更新明细表配置的问题",
            "from_rev": from_rev,
            "to_rev": to_rev,
        }

    return {
        "valid": True,
        "mode": "range",
        "from_rev": from_rev,
        "to_rev": to_rev,
        "batch_message": batch_message,
        "quick_test": quick_test,
    }


def _parse_explicit_mode(
    matches: list[re.Match],
    batch_message: str,
    quick_test: bool,
    raw: str,
) -> dict[str, Any]:
    input_order = [int(m.group("rev")) for m in matches]
    unique = list(dict.fromkeys(input_order))
    analysis_order = sorted(unique)

    if len(analysis_order) < 2:
        return {
            "valid": False,
            "mode": "single",
            "error": f"仅识别到 {len(analysis_order)} 笔 revision，请提供 2–10 笔",
            "input_order": input_order,
            "analysis_order": analysis_order,
        }

    if len(analysis_order) > MAX_BATCH_SIZE:
        return {
            "valid": False,
            "mode": "explicit",
            "error": f"实际 revision 数量 {len(analysis_order)} 超过上限 {MAX_BATCH_SIZE}",
            "input_order": input_order,
            "analysis_order": analysis_order,
        }

    if not batch_message:
        return {
            "valid": False,
            "mode": "explicit",
            "error": "缺少 batch_message（批次总结说明）",
            "input_order": input_order,
            "analysis_order": analysis_order,
        }

    return {
        "valid": True,
        "mode": "explicit",
        "input_order": input_order,
        "analysis_order": analysis_order,
        "batch_message": batch_message,
        "quick_test": quick_test,
    }


def validate_batch(
    mode: str,
    revisions: list[int],
    batch_message: str,
    from_rev: int | None = None,
    to_rev: int | None = None,
) -> list[str]:
    """校验批次约束，返回错误列表（空列表 = 通过）。

    在校验前调用（resolver 产生结果后），确保：
    - revision 数量 2–10
    - 区间跨度不超过 10
    - batch_message 非空
    """
    errors: list[str] = []

    if not batch_message.strip():
        errors.append("缺少 batch_message")

    if len(revisions) < 2:
        errors.append(f"至少需要 2 笔 revision，实际 {len(revisions)} 笔。请改用单笔模板")
        return errors

    if len(revisions) > MAX_BATCH_SIZE:
        errors.append(f"revision 数量 {len(revisions)} 超过上限 {MAX_BATCH_SIZE}")

    if mode == "range" and from_rev is not None and to_rev is not None:
        span = to_rev - from_rev
        if span > MAX_RANGE_SPAN:
            errors.append(f"区间跨度 {span} 超过 {MAX_RANGE_SPAN}")

    if len(revisions) == 1:
        errors.append("仅 1 笔 revision，请改用单笔模板")

    return errors


def resolve_revision_set(
    resolver: Callable | None,
    mode: str,
    from_rev: int | None = None,
    to_rev: int | None = None,
    input_order: list[int] | None = None,
) -> dict[str, Any]:
    """通过 MCP（或测试替身）解析实际 revision 集合。

    区间模式：对 A、B 各调用 resolver 取邻域，合并去重后过滤闭区间。
    显式集合：直接返回 input_order（去重排序），不调用 MCP。

    resolver 签名：``resolver(revision: int, before: int, after: int) -> dict``

    返回统一契约（见需求分析 3.4/3.5 节）。
    """
    # ── 显式集合 ──
    if mode == "explicit":
        if input_order is None:
            return _resolver_error("input_rejected", "显式集合缺少 input_order")
        unique = list(dict.fromkeys(input_order))
        analysis_order = sorted(unique)
        if len(analysis_order) > MAX_BATCH_SIZE:
            return _resolver_error(
                "over_limit",
                f"显式集合 revision 数量 {len(analysis_order)} 超过上限 {MAX_BATCH_SIZE}",
            )
        return {
            "schema_version": 1,
            "mode": "explicit",
            "input_order": input_order,
            "analysis_order": analysis_order,
            "resolved_revisions": analysis_order,
            "skipped_revisions": [],
            "complete": True,
            "source": "explicit-input",
            "source_queries": [],
            "boundary_evidence": {},
            "error": None,
            "status": "accepted",
        }

    # ── 区间模式 ──
    if mode == "range":
        if resolver is None:
            return _resolver_error(
                "resolver_unavailable",
                "读取 E9 信息 MCP 不可用，无法解析区间 revision 集合。请检查 MCP 连接或改用显式集合模板",
            )
        return _resolve_range(resolver, from_rev, to_rev)

    return _resolver_error("input_rejected", f"未知模式: {mode}")


def _resolve_range(
    resolver: Callable,
    from_rev: int | None,
    to_rev: int | None,
) -> dict[str, Any]:
    """区间 resolver：对 A、B 各查询邻域，合并去重过滤。"""
    if from_rev is None or to_rev is None:
        return _resolver_error("input_rejected", "区间模式缺少端点")

    if from_rev == to_rev:
        return _resolver_error(
            "input_rejected",
            f"A=B={from_rev}，请使用单笔模板",
        )

    source_queries: list[dict[str, Any]] = []

    # 查询 A 的 after
    try:
        result_a = resolver(revision=from_rev, before=0, after=MAX_RANGE_SPAN)
    except Exception as exc:
        return _resolver_error("resolver_unavailable", f"端点 A({from_rev}) 查询失败: {exc}")
    source_queries.append({"endpoint": from_rev, "before": 0, "after": MAX_RANGE_SPAN, "status": "ok" if result_a.get("ok") else "failed"})

    # 查询 B 的 before
    try:
        result_b = resolver(revision=to_rev, before=MAX_RANGE_SPAN, after=0)
    except Exception as exc:
        return _resolver_error("resolver_unavailable", f"端点 B({to_rev}) 查询失败: {exc}")
    source_queries.append({"endpoint": to_rev, "before": MAX_RANGE_SPAN, "after": 0, "status": "ok" if result_b.get("ok") else "failed"})

    # 校验端点存在
    if not result_a.get("ok") or not result_a.get("anchor"):
        return _resolver_error(
            "incomplete",
            f"端点 A({from_rev}) 在 MCP 返回中不存在或查询失败",
            source_queries=source_queries,
        )
    if not result_b.get("ok") or not result_b.get("anchor"):
        return _resolver_error(
            "incomplete",
            f"端点 B({to_rev}) 在 MCP 返回中不存在或查询失败",
            source_queries=source_queries,
        )

    # 边界证据校验
    boundary_a = result_a.get("boundary") or {}
    boundary_b = result_b.get("boundary") or {}
    if not boundary_a or not boundary_b:
        return _resolver_error(
            "incomplete",
            "MCP 返回缺少 boundary 边界证据字段，无法确认区间完整性",
            source_queries=source_queries,
        )

    # 收集所有 revision
    all_revs: dict[int, dict] = {}
    # 锚点 A
    anchor_a = result_a["anchor"]
    all_revs[anchor_a["revision"]] = anchor_a
    for item in result_a.get("after") or []:
        all_revs[item["revision"]] = item

    # 锚点 B
    anchor_b = result_b["anchor"]
    all_revs[anchor_b["revision"]] = anchor_b
    for item in result_b.get("before") or []:
        all_revs[item["revision"]] = item

    # 过滤闭区间 [from_rev, to_rev] 并升序
    resolved = sorted(
        rev for rev in all_revs if from_rev <= rev <= to_rev
    )

    # 计算 skipped
    skipped: list[int] = []
    for rev in range(from_rev, to_rev + 1):
        if rev not in all_revs:
            skipped.append(rev)

    # 截断检测
    window_a = result_a.get("window") or {}
    window_b = result_b.get("window") or {}
    a_truncated = window_a.get("after_truncated", False)
    b_truncated = window_b.get("before_truncated", False)

    # 完整性判定
    complete = True
    error_msg = None

    # 双边截断：A 和 B 的查询窗口都被截断，即使端点都在，也无法保证区间完整
    if a_truncated and b_truncated:
        complete = False
        error_msg = "A 端和 B 端查询窗口均被截断，区间结果可能不完整"
    elif a_truncated and to_rev not in all_revs:
        complete = False
        error_msg = "A 端查询窗口被截断且未覆盖到 B 端，区间结果可能不完整"
    elif b_truncated and from_rev not in all_revs:
        complete = False
        error_msg = "B 端查询窗口被截断且未覆盖到 A 端，区间结果可能不完整"

    if len(resolved) > MAX_BATCH_SIZE:
        complete = False
        error_msg = f"区间内实际 revision 数量 {len(resolved)} 超过上限 {MAX_BATCH_SIZE}"

    status = "accepted" if complete else "incomplete"

    return {
        "schema_version": 1,
        "mode": "range",
        "input_order": [from_rev, to_rev],
        "analysis_order": resolved,
        "resolved_revisions": resolved,
        "skipped_revisions": skipped,
        "complete": complete,
        "source": "e9-read-mcp",
        "source_queries": source_queries,
        "boundary_evidence": {
            "lower": "confirmed" if from_rev in all_revs else "missing",
            "upper": "confirmed" if to_rev in all_revs else "missing",
        },
        "error": error_msg,
        "status": status,
    }


def _resolver_error(
    status: str,
    error: str,
    source_queries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "",
        "input_order": [],
        "analysis_order": [],
        "resolved_revisions": [],
        "skipped_revisions": [],
        "complete": False,
        "source": "",
        "source_queries": source_queries or [],
        "boundary_evidence": {},
        "error": error,
        "status": status,
    }


def generate_batch_id(analysis_order: list[int]) -> str:
    """按 analysis_order 首尾 revision 生成稳定 batch_id。

    示例：``[349181, 349182, 349183, 349184]`` → ``"batch_r349181_r349184"``
    """
    if not analysis_order:
        return "batch_empty"
    if len(analysis_order) == 1:
        return f"batch_r{analysis_order[0]}"
    return f"batch_r{analysis_order[0]}_r{analysis_order[-1]}"


_run_id_counter = 0


def generate_analysis_run_id(batch_id: str) -> str:
    """生成唯一 analysis_run_id，防止重跑覆盖历史产物。

    格式：``<batch_id>-<timestamp_us>-<seq>``
    """
    global _run_id_counter
    timestamp = str(int(time.time() * 1_000_000))
    _run_id_counter += 1
    return f"{batch_id}-{timestamp}-{_run_id_counter}"


# ── 多标记工具 ────────────────────────────────────────────────────


def generate_batch_marks(revisions: list[int]) -> list[str]:
    """为批次用例生成全部 pytest mark 装饰器列表。

    示例：``[349181, 349182]`` → ``["@pytest.mark.r349181", "@pytest.mark.r349182"]``
    """
    return [f"@pytest.mark.r{rev}" for rev in sorted(revisions)]


def generate_batch_mark_expression(revisions: list[int]) -> str:
    """生成批次 OR 表达式，用于 pytest -m 选择。

    示例：``[349181, 349182, 349183]`` → ``"r349181 or r349182 or r349183"``
    """
    deduped = sorted(set(revisions))
    marks = [f"r{rev}" for rev in deduped]
    return " or ".join(marks)


def validate_mark_expression(expression: str) -> tuple[bool, str]:
    """校验 mark 表达式是否合法（仅含 r<digits> 和 or/and/not/括号）。

    返回 ``(is_valid, error_message)``。
    """
    if not expression or not expression.strip():
        return False, "表达式为空"
    # 允许的 token：r<digits>、or、and、not、括号、空格
    allowed = re.compile(r"^(r\d+|or|and|not|[()]|\s)+$")
    if not allowed.match(expression.strip()):
        return False, f"表达式包含非法字符: {expression!r}"
    # 至少包含一个 r<digits>
    if not re.search(r"r\d+", expression):
        return False, "表达式未包含任何 revision mark"
    return True, ""


def parse_batch_marks_from_text(text: str) -> list[int]:
    """从用例源码文本中提取所有 r<digits> mark。

    示例：``"@pytest.mark.r349181\\n@pytest.mark.r349182"`` → ``[349181, 349182]``
    """
    raw_marks = re.findall(r"r(\d+)", text)
    return sorted(set(int(m) for m in raw_marks))