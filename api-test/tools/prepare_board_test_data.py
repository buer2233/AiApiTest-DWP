# -*- coding: utf-8 -*-
"""r349149 阶段 C 前置数据准备工具。

基于 E9 数据中心（board）后端 API 自动构建两个测试组件：

- ``E9_R349149_WIDGET_ID``：任一可查询的 DIGITALPANEL（数字面板）组件；
- ``E9_R349149_FILTER_WIDGET_ID``：配置了「不包含」负向过滤条件、
  且过滤字段经探测确认含空值数据的组件（P0 空值口径验证专用）。

链路（由 E9 MCP 知识图谱与源码反查确认）：
``dm/listAll`` 选模型 → ``dm/tableMeta/list`` 选 CHAR 字段 →
``dashboard/create`` 建看板 → ``widget/create`` 建组件 →
``getDataWithConfig``（LZW 载荷）探测空值字段 → ``widget/config`` 写入过滤条件。

用法（在 api-test/ 下）：
    python tools/prepare_board_test_data.py             # 构建并输出环境变量
    python tools/prepare_board_test_data.py --cleanup   # 回收全部构建数据
    python tools/prepare_board_test_data.py --dm-id <模型id>  # 指定数据模型

产物状态写入 ``test_data/board/board_test_data.json``——测试用例依赖的数据
属于交付物，纳入 Git 管理并按模块分目录（勿放 runtime/）；重复执行幂等复用。
本工具只使用管理员账号在测试环境创建可回收数据，不读取或输出任何凭据。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from page_api.board_api.board_api import BoardAPI  # noqa: E402
from page_api.board_api.board_widget_api import (  # noqa: E402
    BoardWidgetAPI,
    build_widget_config_data,
)
from page_api.login_api.login_api import LoginAPI  # noqa: E402
from page_api.public.api_context import APIContext  # noqa: E402
from utils.common_function import load_account  # noqa: E402

BOARD_NAME = "r349149自动化测试看板"
WIDGET_NAME = "r349149自动化测试组件"
FILTER_WIDGET_NAME = "r349149自动化测试过滤组件"
PROBE_VALUE = "zz_r349149_probe_zz"
STATE_PATH = PROJECT_ROOT / "test_data" / "board" / "board_test_data.json"
MAX_PROBE_FIELDS = 6
EMPTY_MARKS = {"", "null", "none", "-"}


def log(message: str) -> None:
    print(f"[r349149-prep] {message}")


def fail(message: str) -> int:
    print(f"[r349149-prep] 失败：{message}", file=sys.stderr)
    return 1


def login_admin() -> APIContext:
    """按框架 fixture 同样的步骤登录管理员，返回共享会话上下文。"""
    account = load_account("admin")
    if not account.get("user_name") or not account.get("password"):
        raise RuntimeError("管理员账号未配置（config.json admin 字段）")
    api = LoginAPI()
    api._caller = account["user_name"]
    api.get_rsa_info()
    response = api.check_login(
        loginid=account["user_name"],
        userpassword=account["password"],
    )
    if response.get("msgcode") != "0" or response.get("loginstatus") != "true":
        raise RuntimeError(f"管理员登录失败: {LoginAPI.safe_login_fields(response)}")
    api.remind_login()
    api.is_weak_password(password=account["password"])
    api.get_os_info()
    return APIContext(api, caller=account["user_name"])


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def require_ok(response: object, action: str) -> dict:
    """Result 统一校验：api_status 必须为 True，返回响应字典。"""
    if not isinstance(response, dict) or response.get("api_status") is not True:
        raise RuntimeError(f"{action} 未成功: api_status={response.get('api_status') if isinstance(response, dict) else type(response).__name__}")
    return response


def pick_data_model(board_api: BoardAPI, dm_id_arg: str) -> tuple[str, str, str]:
    """选择数据模型，返回 (分组 id, 模型 id, 模型名)。"""
    response = require_ok(board_api.list_all_data_models(), "查询数据模型列表")
    groups = response.get("data") or []
    if not isinstance(groups, list) or not groups:
        raise RuntimeError("环境中没有任何数据模型，请先在数据中心创建")
    if dm_id_arg:
        for group in groups:
            for item in group.get("items") or []:
                if str(item.get("id")) == str(dm_id_arg):
                    return str(group.get("groupId") or ""), str(item["id"]), str(item.get("name") or "")
        raise RuntimeError(f"指定的数据模型 {dm_id_arg} 不在 listAll 结果中")
    for group in groups:
        items = group.get("items") or []
        if items:
            first = items[0]
            return str(group.get("groupId") or ""), str(first["id"]), str(first.get("name") or "")
    raise RuntimeError("所有数据模型分组均为空")


def _field_name_of(field: dict) -> str:
    return str(field.get("name") or field.get("fieldName") or "")


def _field_type_of(field: dict) -> str:
    return str(field.get("type") or field.get("fieldType") or field.get("columnType") or "").upper()


def pick_char_fields(board_api: BoardAPI, dm_id: str) -> tuple[str, list[str]]:
    """取模型第一张表的 CHAR 类字段候选，返回 (表名, 字段名列表)。"""
    response = require_ok(board_api.list_table_meta(dm_id), "查询数据模型表元数据")
    tables = response.get("data") or []
    if not isinstance(tables, list) or not tables:
        raise RuntimeError("数据模型没有可用的表")
    table = tables[0]
    table_name = str(table.get("name") or "")
    candidates: list[str] = []
    fallback: list[str] = []
    for field in table.get("fields") or []:
        if not isinstance(field, dict):
            continue
        name = _field_name_of(field)
        if not name:
            continue
        ftype = _field_type_of(field)
        if "LOB" in ftype or "CLOB" in ftype:
            continue
        if not ftype or "CHAR" in ftype or "TEXT" in ftype:
            candidates.append(name)
        fallback.append(name)
    chosen = candidates or fallback
    if not table_name or not chosen:
        raise RuntimeError("数据模型表中没有可用字段")
    return table_name, chosen[:MAX_PROBE_FIELDS]


def create_widget(widget_api: BoardWidgetAPI, board_id: str, dm_id: str, name: str) -> str:
    """创建 DIGITALPANEL 组件并返回组件 id。"""
    response = require_ok(
        widget_api.create_widget(
            name=name,
            widget_type="DIGITALPANEL",
            board=board_id,
            datamodel=dm_id,
            dm_type="DB_DATAMODEL",
        ),
        f"创建组件 {name}",
    )
    data = response.get("data") or {}
    widget_id = str(data.get("id") or "") if isinstance(data, dict) else str(data)
    if not widget_id:
        raise RuntimeError(f"创建组件 {name} 未返回 id")
    return widget_id


def _probe_payload(dm_id: str, table_name: str, field: str, with_filter: bool) -> str:
    """构造 BAR 形态的 getDataWithConfig 载荷（维度 + COUNT 度量 ± 不包含过滤）。"""
    dimensions = [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                   "orderType": "DEFAULT", "shortKey": "d1", "showName": field}]
    measures = [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                 "aggregator": "COUNT", "shortKey": "m1", "orderType": "DEFAULT",
                 "showName": f"{field}-计数"}]
    filters = []
    if with_filter:
        filters = [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                    "shortIndex": "0",
                    "content": {"conditions": [{"func": "uncontains", "value": PROBE_VALUE}]}}]
    return build_widget_config_data(
        datamodel=dm_id,
        config="",
        dimensions=dimensions,
        measures=measures,
        filters=filters,
        widget_type="BAR",
    )


def find_rows(payload: object) -> list[dict] | None:
    """递归查找响应中最大的字典列表，作为数据行候选。"""
    best: list[dict] = []

    def walk(node: object) -> None:
        nonlocal best
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            dicts = [item for item in node if isinstance(item, dict)]
            if len(dicts) > len(best):
                best = dicts
            for item in node:
                walk(item)

    walk(payload)
    return best or None


def row_has_empty_dimension(row: dict, field: str) -> bool:
    """判断某行在维度字段上是否为空值（null 组）。"""
    keys = [field, "d1", "name", "text", "label", "x", "value"]
    for key in keys:
        if key in row and str(row.get(key) or "").strip().lower() in EMPTY_MARKS:
            return True
    return False


def probe_null_field(
    widget_api: BoardWidgetAPI,
    dm_id: str,
    table_name: str,
    candidates: list[str],
) -> str | None:
    """用 getDataWithConfig 逐个探测候选字段，返回含空值数据的字段名。

    入选条件只看基础响应是否存在空值维度组；过滤前后行数差异仅作为
    环境部署版本的诊断信息（过滤后为空通常意味着环境仍在运行 r349149
    修复前的代码，属预期差异，不影响数据准备）。
    """
    for field in candidates:
        try:
            base = widget_api.get_data_with_config(_probe_payload(dm_id, table_name, field, False))
            filtered = widget_api.get_data_with_config(_probe_payload(dm_id, table_name, field, True))
        except Exception as exc:  # noqa: BLE001 — 探测失败换下一个字段
            log(f"字段 {field} 探测异常，跳过：{exc}")
            continue
        base_rows = find_rows(base)
        if base_rows is None:
            preview = json.dumps(base, ensure_ascii=False)[:200] if isinstance(base, dict) else str(type(base))
            log(f"字段 {field} 基础响应中未识别到数据行，跳过。响应预览：{preview}")
            continue
        filtered_rows = find_rows(filtered) or []
        if any(row_has_empty_dimension(row, field) for row in base_rows):
            env_note = (
                "过滤后行数不少于基础行数（环境表现符合 r349149 修复后口径）"
                if len(filtered_rows) >= len(base_rows)
                else "过滤后行数减少（环境可能尚未部署 r349149，测试执行时按版本差异假设分析）"
            )
            log(f"字段 {field} 命中空值数据（基础 {len(base_rows)} 行 / 过滤后 {len(filtered_rows)} 行）；{env_note}")
            return field
        log(f"字段 {field} 无空值数据（{len(base_rows)} 行），继续探测")
    return None


def configure_filter_widget(
    widget_api: BoardWidgetAPI,
    widget_id: str,
    dm_id: str,
    table_name: str,
    field: str,
) -> None:
    """给组件写入「不包含」过滤条件（widget/config，LZW 载荷）。"""
    payload = {
        "id": widget_id,
        "name": FILTER_WIDGET_NAME,
        "type": "DIGITALPANEL",
        "datamodel": dm_id,
        "dmType": "DB_DATAMODEL",
        "config": "",
        "dimensions": [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                        "orderType": "DEFAULT", "shortKey": "d1", "showName": field,
                        "shortIndex": "0"}],
        "measures": [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                      "aggregator": "COUNT", "shortKey": "m1", "orderType": "DEFAULT",
                      "showName": f"{field}-计数", "showType": "", "showPattern": "",
                      "combinationType": "", "shortIndex": "0"}],
        "filters": [{"tableName": table_name, "fieldName": field, "fieldType": "CHAR",
                     "shortIndex": "0",
                     "content": {"conditions": [{"func": "uncontains", "value": PROBE_VALUE}]}}],
    }
    require_ok(
        widget_api.config_widget(json.dumps(payload, ensure_ascii=False)),
        "写入组件过滤条件",
    )


def cleanup(state: dict, ctx: APIContext) -> None:
    """回收构建的组件与看板。"""
    board_api = ctx.use(BoardAPI)
    widget_api = ctx.use(BoardWidgetAPI)
    for key in ("filter_widget_id", "widget_id"):
        widget_id = state.get(key)
        if widget_id:
            try:
                widget_api.delete_widget(widget_id)
                log(f"已删除组件 {widget_id}")
            except Exception as exc:  # noqa: BLE001 — 清理尽量执行
                log(f"删除组件 {widget_id} 失败：{exc}")
    board_id = state.get("board_id")
    if board_id:
        try:
            board_api.delete_dashboard(board_id)
            log(f"已删除看板 {board_id}")
        except Exception as exc:  # noqa: BLE001 — 清理尽量执行
            log(f"删除看板 {board_id} 失败：{exc}")
    if STATE_PATH.exists():
        STATE_PATH.unlink()
        log("已删除状态文件")


def main() -> int:
    parser = argparse.ArgumentParser(description="r349149 阶段 C 前置数据准备")
    parser.add_argument("--dm-id", default="", help="指定数据模型 id（默认取 listAll 第一个）")
    parser.add_argument("--cleanup", action="store_true", help="回收全部构建数据后退出")
    args = parser.parse_args()

    try:
        ctx = login_admin()
    except Exception as exc:  # noqa: BLE001
        return fail(f"登录失败：{exc}")
    log("管理员登录成功")

    state = load_state()
    if args.cleanup:
        cleanup(state, ctx)
        return 0

    board_api = ctx.use(BoardAPI)
    widget_api = ctx.use(BoardWidgetAPI)

    try:
        if state.get("widget_id") and state.get("filter_widget_id") and state.get("field"):
            log("检测到已有构建状态，幂等复用（如需重建请先 --cleanup）")
        else:
            group_id, dm_id, dm_name = pick_data_model(board_api, args.dm_id)
            log(f"选用数据模型：{dm_name or dm_id}（分组 {group_id or '无'}）")
            table_name, candidates = pick_char_fields(board_api, dm_id)
            log(f"选用表 {table_name}，候选字段 {candidates}")

            board_id = state.get("board_id") or ""
            if not board_id:
                response = require_ok(board_api.create_dashboard(BOARD_NAME, group_id), "创建看板")
                data = response.get("data") or {}
                board_id = str(data.get("id") or "") if isinstance(data, dict) else str(data)
                if not board_id:
                    return fail("创建看板未返回 id")
                log(f"已创建看板 {board_id}（{BOARD_NAME}）")

            widget_id = state.get("widget_id") or create_widget(widget_api, board_id, dm_id, WIDGET_NAME)
            log(f"组件一（任一可查询数字面板）：{widget_id}")

            field = probe_null_field(widget_api, dm_id, table_name, candidates)
            if not field:
                save_state({**state, "board_id": board_id, "widget_id": widget_id,
                            "dm_id": dm_id, "table": table_name})
                return fail(
                    f"候选字段 {candidates} 均未探测到空值数据；"
                    "请更换数据模型（--dm-id）或人工指定含空值字段的模型"
                )

            filter_widget_id = create_widget(widget_api, board_id, dm_id, FILTER_WIDGET_NAME)
            configure_filter_widget(widget_api, filter_widget_id, dm_id, table_name, field)
            log(f"组件二（含「不包含」过滤条件）：{filter_widget_id}，过滤字段 {field}")

            state = {
                "board_id": board_id,
                "widget_id": widget_id,
                "filter_widget_id": filter_widget_id,
                "dm_id": dm_id,
                "table": table_name,
                "field": field,
                "probe_value": PROBE_VALUE,
            }
            save_state(state)

        print()
        print(f"E9_R349149_WIDGET_ID={state.get('widget_id', '')}")
        print(f"E9_R349149_FILTER_WIDGET_ID={state.get('filter_widget_id', '')}")
        print()
        log("完成：以上两行可直接设置为环境变量后运行 python runpytest.py -m r349149 --clean")
        return 0
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
