# -*- coding: utf-8 -*-
"""把 facts / design 写成 JSON、HTML、Markdown。"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from svn_analyse.facts import PURE_FRONTEND_MESSAGE
from svn_analyse.revision import revision_mark

DEFAULT_ENV_ASSUMPTION = (
    "测试环境（如 https://test.example）可能尚未部署本 revision。"
    "阶段 B 执行前需确认环境。"
)
NEXT_COMMAND = "按方案实现接口自动化"
PURE_FRONTEND_NEXT_COMMAND = "本提交为纯前端改动，无需实现接口自动化"


def design_skeleton(facts: dict[str, Any]) -> dict[str, Any]:
    """CLI 写出的 design.json 骨架，供 AI 补全功能用例与接口设计。"""
    revision = int(facts.get("revision") or 0)
    mark = revision_mark(revision) if revision else ""
    api_cases = []
    for endpoint in facts.get("endpoints") or []:
        existing = [
            item
            for item in (facts.get("existing_api") or [])
            if item.get("url") == endpoint.get("url")
            and (not item.get("http_method") or item.get("http_method") == endpoint.get("method"))
            and item.get("wrapper")
        ]
        hit = existing[0] if existing else {}
        has_wrapper = bool(hit.get("has_wrapper", bool(hit.get("wrapper"))))
        reuse = {
            "has_wrapper": has_wrapper,
            "wrapper": hit.get("wrapper") or "",
            "class_name": hit.get("class_name") or hit.get("class") or "",
            "file": hit.get("file") or "",
            "line": hit.get("line") or 0,
            "http_method": hit.get("http_method") or "",
        }
        api_cases.append(
            {
                "url": endpoint.get("url"),
                "http_method": endpoint.get("method"),
                "action": endpoint.get("action"),
                "reuse": reuse,
                "suggested_wrapper": "" if has_wrapper else "",
                "suggested_test": "",
                "scenarios": ["正常场景", "边界场景", "异常场景"],
                "mark": mark,
            }
        )
    pure_frontend = bool(facts.get("pure_frontend"))
    return {
        "revision": revision,
        "title": facts.get("message") or f"SVN {mark} 影响分析",
        "behavior_change": "",
        "impact_summary": PURE_FRONTEND_MESSAGE if pure_frontend else "",
        "unchanged_paths": [],
        "functional_cases": [],
        "api_cases": [] if pure_frontend else api_cases,
        "risks": list(facts.get("warnings") or []),
        "env_assumption": DEFAULT_ENV_ASSUMPTION,
        "next_command": PURE_FRONTEND_NEXT_COMMAND if pure_frontend else NEXT_COMMAND,
        "confidence": facts.get("confidence") or "medium",
        "pure_frontend": pure_frontend,
        # 四期 T4.2：反查证据包引用；阶段 B 前置数据决策必须读取该文件
        "reverse_lookup": {
            "file": "reverse_lookup.json",
            "entries": len(facts.get("endpoints") or []),
            "frontend_operations": len(facts.get("frontend_operations") or []),
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_outputs(out_dir: str | Path, facts: dict[str, Any], design: dict[str, Any] | None = None) -> dict[str, Path]:
    """写入 facts.json / design.json / report.html / report.md。"""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    resolved_design = design or design_skeleton(facts)
    paths = {
        "facts": dest / "facts.json",
        "design": dest / "design.json",
        "html": dest / "report.html",
        "md": dest / "report.md",
    }
    write_json(paths["facts"], facts)
    write_json(paths["design"], resolved_design)
    paths["html"].write_text(render_html(facts, resolved_design), encoding="utf-8")
    paths["md"].write_text(render_md(facts, resolved_design), encoding="utf-8")
    return paths


def render_from_dir(out_dir: str | Path) -> dict[str, Path]:
    dest = Path(out_dir)
    facts = load_json(dest / "facts.json")
    design_path = dest / "design.json"
    design = load_json(design_path) if design_path.is_file() else design_skeleton(facts)
    return write_outputs(dest, facts, design)


def render_html(facts: dict[str, Any], design: dict[str, Any]) -> str:
    revision = facts.get("revision")
    mark = revision_mark(int(revision)) if revision else ""
    title = design.get("title") or f"SVN {mark} 影响分析与回归方案"
    cases_html = _cases_table(design.get("functional_cases") or [])
    api_html = _api_table(design.get("api_cases") or [])
    files_html = _files_table(facts.get("changed_files") or [])
    pure_frontend = bool(facts.get("pure_frontend") or design.get("pure_frontend"))
    endpoints_html = (
        f'<p class="empty">{_e(PURE_FRONTEND_MESSAGE)}</p>'
        if pure_frontend
        else _endpoints_table(facts.get("endpoints") or [])
    )
    endpoint_diag_html = _endpoint_diag_html(
        facts.get("endpoint_diagnostics") or {}, pure_frontend
    )
    existing_html = (
        f'<p class="empty">{_e(PURE_FRONTEND_MESSAGE)}</p>'
        if pure_frontend
        else _existing_table(facts.get("existing_api") or [])
    )
    impact_html = (
        f'<p class="empty">{_e(PURE_FRONTEND_MESSAGE)}</p>'
        if pure_frontend
        else _impact_table(facts.get("impact") or [])
    )
    warnings = design.get("risks") or facts.get("warnings") or []
    unchanged = design.get("unchanged_paths") or []
    impact_default = (
        PURE_FRONTEND_MESSAGE
        if pure_frontend
        else "以本次 diff 中的符号为中心；被调公共 API 若本体未改，不向外扩散。"
    )
    frontend_banner = (
        f'<div class="callout"><strong>{_e(PURE_FRONTEND_MESSAGE)}</strong>'
        f"<p>已跳过 MCP impact 分析与 HTTP 端点提取。</p></div>"
        if pure_frontend
        else ""
    )
    next_heading = (
        "下一句口令"
        if pure_frontend
        else "下一句口令（阶段 B，不会自动执行）"
    )
    next_hint = (
        ""
        if pure_frontend
        else f'<p class="meta">复测已落地的用例：<code>复测 {_e(mark)}</code></p>'
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)}</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --paper: #fffcf6;
      --ink: #1f2430;
      --muted: #5c6573;
      --line: #d9d1c3;
      --accent: #8a4b1f;
      --p0: #9b2c2c;
      --p1: #8a4b1f;
      --p2: #4d5b4a;
      --ok: #2f5d3a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.65 "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    main {{
      max-width: 1080px;
      margin: 32px auto 64px;
      background: var(--paper);
      border: 1px solid var(--line);
      padding: 40px 48px 56px;
    }}
    h1 {{ font-size: 26px; font-weight: 650; margin: 0 0 8px; }}
    h2 {{
      font-size: 18px;
      margin: 36px 0 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--line);
    }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .badge {{
      display: inline-block;
      padding: 1px 8px;
      border: 1px solid var(--line);
      font-size: 12px;
      letter-spacing: 0.02em;
      margin-right: 8px;
    }}
    .badge.low {{ color: var(--p0); }}
    .badge.medium {{ color: var(--p1); }}
    .badge.high {{ color: var(--ok); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{ background: #f0e9dc; font-weight: 600; }}
    code {{ font-family: Consolas, "Sarasa Mono SC", monospace; font-size: 12.5px; }}
    pre {{
      background: #f0e9dc;
      border: 1px solid var(--line);
      padding: 12px 14px;
      overflow: auto;
      font-size: 12px;
    }}
    .callout {{
      border-left: 3px solid var(--accent);
      background: #f7efe3;
      padding: 10px 14px;
      margin: 12px 0;
    }}
    .next {{
      margin-top: 28px;
      padding: 16px 18px;
      border: 1px dashed var(--accent);
    }}
    ul {{ padding-left: 1.2em; }}
    .empty {{ color: var(--muted); }}
  </style>
</head>
<body>
<main>
  <p class="meta">
    <span class="badge {_e(str(design.get('confidence') or facts.get('confidence') or 'medium'))}">置信度 { _e(str(design.get('confidence') or facts.get('confidence') or 'medium')) }</span>
    <span class="badge">{_e(mark)}</span>
    {"<span class=\"badge\">纯前端</span>" if pure_frontend else ""}
    E9 SVN 影响分析 · 阶段 A 报告
  </p>
  <h1>{_e(title)}</h1>
  <p class="meta">作者 {_e(facts.get('author'))} · {_e(facts.get('date'))} · 工作副本 {_e(facts.get('working_copy_revision'))}</p>
  {frontend_banner}

  <h2>一、提交基本信息</h2>
  <table>
    <tr><th>版本</th><td><code>{_e(mark)}</code></td></tr>
    <tr><th>作者</th><td>{_e(facts.get('author'))}</td></tr>
    <tr><th>时间</th><td>{_e(facts.get('date'))}</td></tr>
    <tr><th>说明</th><td>{_e(facts.get('message'))}</td></tr>
    <tr><th>改动文件数</th><td>{len(facts.get('changed_files') or [])}</td></tr>
  </table>

  <h2>二、代码变更</h2>
  {files_html}
  <h3>行为差异（待确认）</h3>
  {_p(design.get('behavior_change') or 'AI 尚未补全。请对照下方 diff 摘录填写 design.json 的 behavior_change。')}
  <pre>{_e(facts.get('diff_excerpt'))}</pre>

  <h2>三、影响范围</h2>
  {_p(design.get('impact_summary') or impact_default)}
  {impact_html}
  <h3>识别到的 HTTP 入口</h3>
  {endpoints_html}
  {endpoint_diag_html}
  <h3>api-test-E9 已有封装</h3>
  {existing_html}
  <h3>未改路径 / 不必扩散</h3>
  {_list(unchanged) if unchanged else '<p class="empty">暂无。可在 design.json 的 unchanged_paths 中补充。</p>'}

  <h2>四、功能回归用例</h2>
  {cases_html}

  <h2>五、接口自动化设计</h2>
  {api_html}
  <p class="meta">新增用例统一标记 <code>@pytest.mark.{_e(mark)}</code>。已有用例被复用时追加该 mark，不覆盖旧标记。</p>

  <h2>六、风险与环境假设</h2>
  <div class="callout">{_e(design.get('env_assumption') or DEFAULT_ENV_ASSUMPTION)}</div>
  {_list(warnings) if warnings else '<p class="empty">无额外告警。</p>'}

  <div class="next">
    <strong>{next_heading}</strong>
    <p>确认本报告后发送：<code>{_e(design.get('next_command') or (PURE_FRONTEND_NEXT_COMMAND if pure_frontend else NEXT_COMMAND))}</code></p>
    {next_hint}
  </div>
</main>
</body>
</html>
"""


def render_md(facts: dict[str, Any], design: dict[str, Any]) -> str:
    revision = facts.get("revision")
    mark = revision_mark(int(revision)) if revision else ""
    title = design.get("title") or f"SVN {mark} 影响分析与回归方案"
    lines = [
        f"# {title}",
        "",
        f"> 版本 `{mark}` · 作者 {facts.get('author') or '-'} · {facts.get('date') or '-'}",
        f"> 置信度：{design.get('confidence') or facts.get('confidence') or 'medium'}",
        "",
    ]
    if facts.get("pure_frontend") or design.get("pure_frontend"):
        lines += [f"> {PURE_FRONTEND_MESSAGE}", ""]
    lines += [
        "## 一、提交基本信息",
        "",
        f"- 说明：{facts.get('message') or '-'}",
        f"- 改动文件数：{len(facts.get('changed_files') or [])}",
        "",
        "## 二、代码变更",
        "",
    ]
    for item in facts.get("changed_files") or []:
        layer = item.get("change_layer")
        extra = f" / {layer}" if layer else ""
        lines.append(f"- `{item.get('action') or '?'} {item.get('path')}` （{item.get('kind')}{extra}）")
    lines += [
        "",
        "### 行为差异",
        "",
        design.get("behavior_change") or "（待 AI 补全 design.json.behavior_change）",
        "",
        "```diff",
        facts.get("diff_excerpt") or "",
        "```",
        "",
        "## 三、影响范围",
        "",
        design.get("impact_summary")
        or (
            PURE_FRONTEND_MESSAGE
            if facts.get("pure_frontend")
            else "以本次 diff 符号为中心；公共 API 本体未改则不扩散。"
        ),
        "",
    ]
    if facts.get("pure_frontend"):
        lines.append(f"- {PURE_FRONTEND_MESSAGE}")
    else:
        for item in facts.get("endpoints") or []:
            via = item.get("via") or "direct"
            lines.append(f"- `{item.get('method')} {item.get('url')}` ← {item.get('action')} （{via}）")
        diag = facts.get("endpoint_diagnostics") or {}
        if not diag.get("skipped"):
            if diag.get("needs_manual_review"):
                lines.append("- ⚠ 端点提取为空，需人工复核（候选见下）")
            for item in diag.get("candidates") or []:
                lines.append(f"  - 候选：`{item.get('file')}` {item.get('class') or ''} — {item.get('reason')}")
        if not (facts.get("endpoints") or []):
            lines.append("- 本提交未识别到稳定 HTTP 入口，接口自动化可空。")
    lines += ["", "## 四、功能回归用例", ""]
    cases = design.get("functional_cases") or []
    if not cases:
        lines.append("（待 AI 按 P0/P1/P2 补全 design.json.functional_cases）")
    else:
        lines.append("| 编号 | 优先级 | 场景 | 操作 | 预期 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for case in cases:
            lines.append(
                "| {id} | {priority} | {scene} | {steps} | {expected} |".format(
                    id=case.get("id") or "",
                    priority=case.get("priority") or "",
                    scene=case.get("scene") or "",
                    steps=case.get("steps") or "",
                    expected=case.get("expected") or "",
                )
            )
    lines += ["", "## 五、接口自动化设计", ""]
    api_cases = design.get("api_cases") or []
    if not api_cases:
        lines.append("无接口入口，或尚未补全 design.json.api_cases。")
    else:
        for case in api_cases:
            lines.append(
                f"- `{case.get('http_method')} {case.get('url')}` reuse={_reuse_label(case.get('reuse'))} mark=`{case.get('mark')}`"
            )
    lines += [
        "",
        "## 六、风险与环境假设",
        "",
        design.get("env_assumption") or DEFAULT_ENV_ASSUMPTION,
        "",
        "## 下一句口令",
        "",
        f"`{design.get('next_command') or NEXT_COMMAND}`",
        "",
    ]
    return "\n".join(lines)


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _p(text: str) -> str:
    return f"<p>{_e(text)}</p>"


def _list(items: list[Any]) -> str:
    rows = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f"<ul>{rows}</ul>"


def _files_table(files: list[dict[str, Any]]) -> str:
    if not files:
        return '<p class="empty">无变更文件。</p>'
    rows = "".join(
        f"<tr><td>{_e(item.get('action'))}</td><td><code>{_e(item.get('path'))}</code></td>"
        f"<td>{_e(item.get('kind'))}</td><td>{_e(item.get('change_layer') or '')}</td></tr>"
        for item in files
    )
    return f"<table><tr><th>动作</th><th>路径</th><th>分类</th><th>判定层</th></tr>{rows}</table>"


def _endpoints_table(endpoints: list[dict[str, Any]]) -> str:
    if not endpoints:
        return '<p class="empty">未识别到稳定 HTTP 入口。本提交可能只需功能测试。</p>'
    rows = "".join(
        f"<tr><td>{_e(item.get('method'))}</td><td><code>{_e(item.get('url'))}</code></td>"
        f"<td>{_e(item.get('action'))}</td><td>{_e(item.get('via') or 'direct')}</td></tr>"
        for item in endpoints
    )
    return f"<table><tr><th>方法</th><th>URL</th><th>Action</th><th>发现策略</th></tr>{rows}</table>"


def _endpoint_diag_html(diag: dict[str, Any] | None, pure_frontend: bool) -> str:
    """四期 T4.1：端点提取诊断区块。纯前端跳过时不渲染。"""
    if pure_frontend or not diag or diag.get("skipped"):
        return ""
    parts: list[str] = []
    if diag.get("needs_manual_review"):
        parts.append(
            '<div class="callout"><strong>端点提取为空，需人工复核。</strong>'
            "<p>下列候选文件未解析出 JAX-RS 注解，请按候选反查 HTTP 入口。</p></div>"
        )
    candidates = diag.get("candidates") or []
    if candidates:
        rows = "".join(
            f"<tr><td><code>{_e(item.get('file'))}</code></td>"
            f"<td>{_e(item.get('class'))}</td><td>{_e(item.get('reason'))}</td></tr>"
            for item in candidates
        )
        parts.append(
            "<h4>候选入口 / 待复核文件</h4>"
            f"<table><tr><th>文件</th><th>类名</th><th>说明</th></tr>{rows}</table>"
        )
    notes = diag.get("notes") or []
    if notes:
        parts.append(_list(notes))
    return "".join(parts)


def _existing_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">api-test-E9 中尚未匹配到这些 URL。</p>'
    rows = "".join(
        f"<tr><td><code>{_e(item.get('url'))}</code></td><td>{_e(item.get('wrapper') or '未封装')}</td>"
        f"<td>{_e(', '.join(item.get('tests') or []))}</td></tr>"
        for item in items
    )
    return f"<table><tr><th>URL</th><th>已有封装</th><th>已有用例</th></tr>{rows}</table>"


def _impact_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">无 MCP impact 数据（索引更新失败或未查到符号）。</p>'
    rows = "".join(
        f"<tr><td>{_e(item.get('symbol'))}</td><td>{_e(item.get('size'))}</td><td>{_e(item.get('note'))}</td></tr>"
        for item in items
    )
    return f"<table><tr><th>符号</th><th>规模</th><th>说明</th></tr>{rows}</table>"


def _cases_table(cases: list[dict[str, Any]]) -> str:
    if not cases:
        return '<p class="empty">待 AI 按 P0 / P1 / P2 补全 <code>design.json</code> 的 <code>functional_cases</code>，然后执行 <code>python -m svn_analyse render output/rXXXX</code>。</p>'
    rows = "".join(
        f"<tr><td>{_e(item.get('id'))}</td><td>{_e(item.get('priority'))}</td>"
        f"<td>{_e(item.get('scene'))}</td><td>{_e(item.get('steps'))}</td>"
        f"<td>{_e(item.get('expected'))}</td></tr>"
        for item in cases
    )
    return f"<table><tr><th>编号</th><th>优先级</th><th>场景</th><th>操作</th><th>预期</th></tr>{rows}</table>"


def _api_table(cases: list[dict[str, Any]]) -> str:
    if not cases:
        return '<p class="empty">无接口自动化设计项。</p>'
    rows = "".join(
        f"<tr><td>{_e(item.get('http_method'))}</td><td><code>{_e(item.get('url'))}</code></td>"
        f"<td>{_e(_reuse_label(item.get('reuse')))}</td><td>{_e(item.get('suggested_wrapper') or item.get('suggested_test'))}</td>"
        f"<td>{_e(', '.join(item.get('scenarios') or []))}</td><td><code>{_e(item.get('mark'))}</code></td></tr>"
        for item in cases
    )
    return (
        "<table><tr><th>方法</th><th>URL</th><th>复用</th><th>建议封装/用例</th>"
        "<th>场景</th><th>mark</th></tr>"
        f"{rows}</table>"
    )


def _reuse_label(reuse: Any) -> str:
    """将结构化复用判定转换为报告中的简短说明。"""
    if isinstance(reuse, dict):
        if not reuse.get("has_wrapper"):
            return "未封装"
        return str(reuse.get("wrapper") or "已封装")
    return str(reuse or "未封装")
