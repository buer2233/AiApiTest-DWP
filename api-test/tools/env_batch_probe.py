# -*- coding: utf-8 -*-
"""四期 T4.5：批量环境探针与前后版本对比。

一次批量探针完成：登录态复用验证 → 环境路由可达性 → 各 revision
行为变更点的前后版本对比。登录只执行一次，后续探针全部复用同一
会话；单个探针失败不阻断其余探针，结论统一写入
``runtime/env_probe_summary.json``（可再生产物，不入 Git）。

对比结果 schema（每条行为探针）：

```json
{
  "name": "r349149_board_filter_behavior",
  "kind": "behavior_compare",
  "status": "ok|failed|skipped",
  "revision": 349149,
  "before_characteristic": "修复前口径描述",
  "after_characteristic": "修复后口径描述",
  "observed": {},
  "deployed": true,
  "revision_assumption": ""
}
```

环境未部署目标 revision 时 ``deployed=false`` 并填写
``revision_assumption``；行为差异只作为信息性证据，不定性为产品缺陷。
本探针不读取或输出凭据，仅输出业务探测结论。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from page_api.board_api.board_api import BoardAPI  # noqa: E402
from page_api.board_api.board_widget_api import BoardWidgetAPI  # noqa: E402
from tools.prepare_board_test_data import (  # noqa: E402
    _probe_payload,
    find_rows,
    load_state as load_board_state,
    login_admin,
)
from tools.prepare_doc_func_test_data import (  # noqa: E402
    probe_download,
    load_state as load_doc_state,
    STATE_PATH as DOC_STATE_PATH,
)

PROBE_SCHEMA_VERSION = "t4.5-v1"
SUMMARY_PATH = PROJECT_ROOT / "runtime" / "env_probe_summary.json"
ASSUMPTION_UNCONFIRMED = (
    "测试环境部署版本尚未确认，行为差异仅作信息性证据，不定性为产品缺陷"
)


def log(message: str) -> None:
    print(f"[env-probe] {message}")


def _result(name: str, status: str, detail: str = "", **extra) -> dict:
    payload = {"name": name, "kind": extra.pop("kind", "probe"), "status": status, "detail": detail}
    payload.update(extra)
    return payload


def _load_state(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def probe_login_reuse(ctx) -> dict:
    """同一会话连续两次跨模块调用，验证登录态复用（不重复登录）。"""
    try:
        board_api = ctx.use(BoardAPI)
        first = board_api.list_all_data_models()
        second = board_api.list_all_data_models()
        ok = (
            isinstance(first, dict)
            and first.get("api_status") is True
            and isinstance(second, dict)
            and second.get("api_status") is True
        )
        if ok:
            return _result("login_reuse", "ok", "单次登录，跨模块复用会话成功")
        return _result("login_reuse", "failed", "复用会话调用未返回成功标志")
    except Exception as exc:  # noqa: BLE001 — 探针失败不阻断批量
        return _result("login_reuse", "failed", f"复用会话调用异常：{exc}")


def probe_route(base_url: str) -> dict:
    """环境路由可达性：base_url 根路径返回非 5xx 即视为可达。"""
    try:
        response = requests.get(base_url, verify=False, timeout=20, allow_redirects=True)
        reachable = response.status_code < 500
        return _result(
            "route_reachable",
            "ok" if reachable else "failed",
            f"HTTP {response.status_code}",
        )
    except requests.RequestException as exc:
        return _result("route_reachable", "failed", f"环境不可达：{exc}")


def probe_board_behavior(ctx) -> dict:
    """r349149 行为对比：负向过滤前后行数差异（空值组口径）。"""
    revision = 349149
    before = "过滤后行数减少（空值组被排除，修复前口径）"
    after = "过滤后行数不少于基础行数（空值组保留，修复后口径）"
    state = load_board_state()
    if not (state.get("widget_id") and state.get("dm_id") and state.get("field")):
        return _result(
            "r349149_board_filter_behavior", "skipped",
            "board 状态基线缺失，先运行 python -m tools.test_data_runner build --module board",
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            deployed=None, revision_assumption=ASSUMPTION_UNCONFIRMED,
        )
    try:
        widget_api = ctx.use(BoardWidgetAPI)
        base_rows = find_rows(widget_api.get_data_with_config(
            _probe_payload(state["dm_id"], state["table"], state["field"], False)
        )) or []
        filtered_rows = find_rows(widget_api.get_data_with_config(
            _probe_payload(state["dm_id"], state["table"], state["field"], True)
        )) or []
        deployed = len(filtered_rows) >= len(base_rows)
        return _result(
            "r349149_board_filter_behavior", "ok",
            f"基础 {len(base_rows)} 行 / 过滤后 {len(filtered_rows)} 行",
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            observed={"base_rows": len(base_rows), "filtered_rows": len(filtered_rows)},
            deployed=deployed,
            revision_assumption="" if deployed else f"环境可能尚未部署 r{revision}，" + ASSUMPTION_UNCONFIRMED,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "r349149_board_filter_behavior", "failed", str(exc),
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            deployed=None, revision_assumption=ASSUMPTION_UNCONFIRMED,
        )


def probe_doc_func_behavior(session_cookies: dict) -> dict:
    """r349155 行为对比：无后缀附件 generateDocZip 是否返回 code=1。"""
    revision = 349155
    before = "generateDocZip 对无后缀附件返回 code=0（误判无下载文件，修复前口径）"
    after = "generateDocZip 对无后缀附件返回 code=1（正常下载，修复后口径）"
    state = _load_state(DOC_STATE_PATH)
    doc_id = state.get("doc_id") or ""
    if not doc_id:
        return _result(
            "r349155_doc_zip_behavior", "skipped",
            "doc_func 状态基线缺失，先运行 python -m tools.test_data_runner build --module doc_func",
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            deployed=None, revision_assumption=ASSUMPTION_UNCONFIRMED,
        )
    try:
        probe = probe_download(config.base_url, session_cookies, doc_id)
        deployed = probe.get("code") == 1
        return _result(
            "r349155_doc_zip_behavior", "ok",
            f"generateDocZip 返回 code={probe.get('code')}",
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            observed={"code": probe.get("code")},
            deployed=deployed,
            revision_assumption="" if deployed else f"环境可能尚未部署 r{revision}，" + ASSUMPTION_UNCONFIRMED,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "r349155_doc_zip_behavior", "failed", str(exc),
            kind="behavior_compare", revision=revision,
            before_characteristic=before, after_characteristic=after,
            deployed=None, revision_assumption=ASSUMPTION_UNCONFIRMED,
        )


def run_batch(modules: list[str] | None = None) -> dict:
    """执行批量探针：一次登录、全部探针、统一汇总。"""
    selected = set(modules or ["board", "doc_func"])
    results: list[dict] = []
    started = time.time()

    route = probe_route(config.base_url)
    results.append(route)

    ctx = None
    if route["status"] == "ok":
        try:
            ctx = login_admin()
            results.append(_result("admin_login", "ok", "管理员登录成功，会话供后续探针复用"))
        except Exception as exc:  # noqa: BLE001
            results.append(_result("admin_login", "failed", f"登录失败：{exc}"))
    else:
        results.append(_result("admin_login", "skipped", "环境不可达，跳过登录"))

    if ctx is not None:
        results.append(probe_login_reuse(ctx))
    else:
        results.append(_result("login_reuse", "skipped", "无可用会话"))

    if "board" in selected:
        if ctx is not None:
            results.append(probe_board_behavior(ctx))
        else:
            results.append(_result("r349149_board_filter_behavior", "skipped", "无可用会话"))
    if "doc_func" in selected:
        if ctx is not None:
            session = getattr(getattr(ctx, "login", None), "base_request", None)
            cookies = session.cookies.get_dict() if session is not None else {}
            results.append(probe_doc_func_behavior(cookies))
        else:
            results.append(_result("r349155_doc_zip_behavior", "skipped", "无可用会话"))

    summary = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "elapsed_seconds": round(time.time() - started, 2),
        "results": results,
        "revision_assumptions": [
            item.get("revision_assumption")
            for item in results
            if item.get("revision_assumption")
        ],
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E9 批量环境探针与前后版本对比（四期 T4.5）")
    parser.add_argument(
        "--modules",
        default="board,doc_func",
        help="参与行为对比的模块，逗号分隔；默认 board,doc_func",
    )
    args = parser.parse_args(argv)
    modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    summary = run_batch(modules)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failed = [item["name"] for item in summary["results"] if item["status"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
