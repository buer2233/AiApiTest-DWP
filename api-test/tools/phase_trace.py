# -*- coding: utf-8 -*-
"""四期 T4.6：全流程阶段 Trace 采集适配器。

为阶段 A/B/C、MCP 查询、源码反查、数据构建、pytest、清理分别
记录结构化 span 与事件，修复 trace 中段断档：相邻确证 span 之间的
空档由渲染器补成「估算」span，报告得以按阶段还原墙钟时间。

Trace 文件：``runtime/trace/r<rev>_trace.json``（可再生产物，不入 Git）。
本模块只采集阶段名、步骤、耗时、状态与错误类型；**不采集**凭据、
Cookie、完整请求头/响应体。

Span schema（t4.6-v1）：

```json
{
  "span_id": "sp-0001",
  "trace_id": "r349155",
  "revision": 349155,
  "phase": "stage_a|mcp_query|reverse_lookup|stage_b|data_build|stage_c|cleanup|report_analysis",
  "step": "analyse",
  "started_at": "2026-08-21T10:00:00",
  "ended_at": "2026-08-21T10:00:21",
  "duration_ms": 21000,
  "status": "ok|failed|running",
  "error_type": "",
  "measured": "confirmed|estimated"
}
```

命令行用法（在 api-test/ 下）：

```powershell
python -m tools.phase_trace begin --revision r349155 --phase stage_a --step analyse
python -m tools.phase_trace end --revision r349155 --span-id sp-0001
python -m tools.phase_trace end --revision r349155 --span-id sp-0002 --status failed --error-type mcp_timeout
python -m tools.phase_trace show --revision r349155
python -m tools.phase_trace report --revision r349155
```
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACE_SCHEMA_VERSION = "t4.6-v1"
TRACE_DIR = PROJECT_ROOT / "runtime" / "trace"

VALID_PHASES = (
    "stage_a",
    "mcp_query",
    "reverse_lookup",
    "stage_b",
    "data_build",
    "stage_c",
    "cleanup",
    "report_analysis",
)
MEASURED_CONFIRMED = "confirmed"
MEASURED_ESTIMATED = "estimated"


class TraceError(RuntimeError):
    """Trace 可预期失败：span 缺失、phase 非法等。"""


def trace_path(revision: int) -> Path:
    return TRACE_DIR / f"r{revision}_trace.json"


def _now() -> datetime:
    return datetime.now()


def load_trace(revision: int) -> dict:
    path = trace_path(revision)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("schema_version", TRACE_SCHEMA_VERSION)
    payload.setdefault("revision", revision)
    payload.setdefault("spans", [])
    payload.setdefault("events", [])
    return payload


def save_trace(revision: int, payload: dict) -> Path:
    path = trace_path(revision)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def begin_span(
    revision: int,
    phase: str,
    step: str,
    started_at: datetime | None = None,
) -> str:
    """开始一个确证 span，返回 span_id。phase 必须取自 VALID_PHASES。"""
    if phase not in VALID_PHASES:
        raise TraceError(f"非法 phase：{phase}；允许值 {VALID_PHASES}")
    payload = load_trace(revision)
    span_id = f"sp-{len(payload['spans']) + 1:04d}"
    start = started_at or _now()
    payload["spans"].append(
        {
            "span_id": span_id,
            "trace_id": f"r{revision}",
            "revision": revision,
            "phase": phase,
            "step": step,
            "started_at": start.isoformat(timespec="seconds"),
            "ended_at": None,
            "duration_ms": None,
            "status": "running",
            "error_type": "",
            "measured": MEASURED_CONFIRMED,
        }
    )
    save_trace(revision, payload)
    return span_id


def end_span(
    revision: int,
    span_id: str,
    status: str = "ok",
    error_type: str = "",
    ended_at: datetime | None = None,
) -> dict:
    """结束 span 并计算耗时；失败时必须给出 error_type 便于定位。"""
    if status not in {"ok", "failed"}:
        raise TraceError("结束状态只能是 ok 或 failed")
    if status == "failed" and not error_type:
        raise TraceError("失败 span 必须提供 error_type")
    payload = load_trace(revision)
    span = next((item for item in payload["spans"] if item["span_id"] == span_id), None)
    if span is None:
        raise TraceError(f"span 不存在：{span_id}")
    end = ended_at or _now()
    start = datetime.fromisoformat(span["started_at"])
    span["ended_at"] = end.isoformat(timespec="seconds")
    span["duration_ms"] = max(0, int((end - start).total_seconds() * 1000))
    span["status"] = status
    span["error_type"] = error_type
    save_trace(revision, payload)
    return span


def record_event(revision: int, phase: str, message: str) -> None:
    """记录一个瞬时事件（如降级告警），不占时间轴区间。"""
    if phase not in VALID_PHASES:
        raise TraceError(f"非法 phase：{phase}；允许值 {VALID_PHASES}")
    payload = load_trace(revision)
    payload["events"].append(
        {
            "at": _now().isoformat(timespec="seconds"),
            "phase": phase,
            "message": message,
        }
    )
    save_trace(revision, payload)


def estimate_gaps(payload: dict) -> list[dict]:
    """在相邻确证 span 之间补估算 span，修复 trace 中段断档。

    只依据时间轴空档推断，标记 measured=estimated、phase=unknown_gap，
    报告渲染时与确证耗时区分展示。
    """
    spans = [item for item in payload.get("spans") or [] if item.get("started_at")]
    ordered = sorted(spans, key=lambda item: item["started_at"])
    gaps: list[dict] = []
    for index in range(1, len(ordered)):
        previous_end = ordered[index - 1].get("ended_at")
        current_start = ordered[index]["started_at"]
        if not previous_end or previous_end >= current_start:
            continue
        start = datetime.fromisoformat(previous_end)
        end = datetime.fromisoformat(current_start)
        duration = int((end - start).total_seconds() * 1000)
        if duration < 1000:
            continue
        gaps.append(
            {
                "span_id": f"gap-{index:04d}",
                "trace_id": ordered[index]["trace_id"],
                "revision": ordered[index]["revision"],
                "phase": "unknown_gap",
                "step": "未采集区间（估算）",
                "started_at": previous_end,
                "ended_at": current_start,
                "duration_ms": duration,
                "status": "ok",
                "error_type": "",
                "measured": MEASURED_ESTIMATED,
            }
        )
    return gaps


def phase_totals(payload: dict, include_gaps: bool = True) -> dict[str, dict[str, int]]:
    """按阶段汇总确证/估算耗时（毫秒）。"""
    totals: dict[str, dict[str, int]] = {}
    spans = list(payload.get("spans") or [])
    if include_gaps:
        spans = spans + estimate_gaps(payload)
    for span in spans:
        if span.get("duration_ms") is None:
            continue
        bucket = totals.setdefault(
            span["phase"], {"confirmed_ms": 0, "estimated_ms": 0, "failed": 0}
        )
        key = "estimated_ms" if span.get("measured") == MEASURED_ESTIMATED else "confirmed_ms"
        bucket[key] += int(span["duration_ms"])
        if span.get("status") == "failed":
            bucket["failed"] += 1
    return totals


def render_trace_html(revision: int, payload: dict | None = None) -> str:
    """渲染阶段 trace 报告：确证与估算耗时分区展示。"""
    data = payload or load_trace(revision)
    spans = sorted(
        list(data.get("spans") or []) + estimate_gaps(data),
        key=lambda item: item.get("started_at") or "",
    )
    totals = phase_totals(data)
    rows = []
    for span in spans:
        measured = span.get("measured") or MEASURED_CONFIRMED
        status_label = {"ok": "成功", "failed": "失败", "running": "进行中"}.get(
            span.get("status") or "", span.get("status") or ""
        )
        rows.append(
            "<tr class=\"{cls}\"><td>{span}</td><td>{phase}</td><td>{step}</td>"
            "<td>{start}</td><td>{end}</td><td>{duration}</td>"
            "<td>{status}</td><td>{error}</td><td>{measured}</td></tr>".format(
                cls="estimated" if measured == MEASURED_ESTIMATED else "confirmed",
                span=html.escape(span.get("span_id") or ""),
                phase=html.escape(span.get("phase") or ""),
                step=html.escape(span.get("step") or ""),
                start=html.escape(span.get("started_at") or ""),
                end=html.escape(span.get("ended_at") or "—"),
                duration=f"{int(span.get('duration_ms') or 0) / 1000:.1f}s",
                status=html.escape(status_label),
                error=html.escape(span.get("error_type") or ""),
                measured="估算" if measured == MEASURED_ESTIMATED else "确证",
            )
        )
    total_rows = []
    for phase, bucket in totals.items():
        total_rows.append(
            f"<tr><td>{html.escape(phase)}</td>"
            f"<td>{bucket['confirmed_ms'] / 1000:.1f}s</td>"
            f"<td>{bucket['estimated_ms'] / 1000:.1f}s</td>"
            f"<td>{bucket['failed']}</td></tr>"
        )
    events = "".join(
        f"<li><code>{html.escape(item.get('at') or '')}</code> "
        f"[{html.escape(item.get('phase') or '')}] {html.escape(item.get('message') or '')}</li>"
        for item in data.get("events") or []
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>r{revision} 阶段 Trace 报告</title>
<style>
body {{ font: 14px/1.6 "Segoe UI", "Microsoft YaHei", sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
th, td {{ border: 1px solid #d9d1c3; padding: 6px 10px; text-align: left; }}
th {{ background: #f0e9dc; }}
tr.estimated td {{ background: #fdf6e3; color: #8a6d1f; }}
tr.confirmed td {{ background: #ffffff; }}
h1 {{ font-size: 20px; }}
.meta {{ color: #5c6573; font-size: 12px; }}
</style>
</head>
<body>
<h1>r{revision} 阶段 Trace 报告</h1>
<p class="meta">schema {html.escape(data.get('schema_version') or TRACE_SCHEMA_VERSION)} ·
确证耗时来自 span 采集；估算耗时为相邻 span 之间的空档推断，仅用于还原墙钟时间。</p>
<h2>阶段耗时汇总</h2>
<table><tr><th>阶段</th><th>确证耗时</th><th>估算耗时</th><th>失败数</th></tr>
{''.join(total_rows) or '<tr><td colspan="4">无 span 数据</td></tr>'}
</table>
<h2>Span 明细</h2>
<table><tr><th>span</th><th>阶段</th><th>步骤</th><th>开始</th><th>结束</th><th>耗时</th><th>状态</th><th>错误类型</th><th>度量</th></tr>
{''.join(rows) or '<tr><td colspan="9">无 span 数据</td></tr>'}
</table>
<h2>事件</h2>
<ul>{events or '<li>无事件</li>'}</ul>
</body>
</html>
"""


def write_trace_report(revision: int, dest: Path | None = None) -> Path:
    path = dest or (TRACE_DIR / f"r{revision}_trace_report.html")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_trace_html(revision), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E9 阶段 Trace 采集适配器（四期 T4.6）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    begin = sub.add_parser("begin", help="开始一个阶段 span")
    begin.add_argument("--revision", required=True, help="r349155 / 349155")
    begin.add_argument("--phase", required=True, help=f"取值：{'/'.join(VALID_PHASES)}")
    begin.add_argument("--step", required=True, help="步骤名，例如 analyse / build / pytest")
    end = sub.add_parser("end", help="结束一个阶段 span")
    end.add_argument("--revision", required=True)
    end.add_argument("--span-id", required=True)
    end.add_argument("--status", default="ok", help="ok 或 failed")
    end.add_argument("--error-type", default="", help="失败时必填，例如 mcp_timeout")
    show = sub.add_parser("show", help="输出 trace JSON")
    show.add_argument("--revision", required=True)
    report = sub.add_parser("report", help="生成 HTML trace 报告")
    report.add_argument("--revision", required=True)
    return parser


def _parse_revision(raw: str) -> int:
    text = str(raw).strip().lstrip("r")
    if not text.isdigit() or int(text) <= 0:
        raise TraceError("revision 必须是正整数（可带 r 前缀）")
    return int(text)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        revision = _parse_revision(args.revision)
        if args.cmd == "begin":
            span_id = begin_span(revision, args.phase, args.step)
            print(json.dumps({"revision": revision, "span_id": span_id}, ensure_ascii=False))
            return 0
        if args.cmd == "end":
            span = end_span(revision, args.span_id, status=args.status, error_type=args.error_type)
            print(
                json.dumps(
                    {"revision": revision, "span_id": span["span_id"], "duration_ms": span["duration_ms"]},
                    ensure_ascii=False,
                )
            )
            return 0
        if args.cmd == "show":
            print(json.dumps(load_trace(revision), ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "report":
            path = write_trace_report(revision)
            print(path)
            return 0
    except TraceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
