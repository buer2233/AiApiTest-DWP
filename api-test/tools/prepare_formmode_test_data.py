# -*- coding: utf-8 -*-
"""r349152 阶段 C 前置数据准备工具。

基于 E9 后端 API 在测试环境自动构建「角色受范围限制权限 + 绑定布局 + 对应单据」
这一组前置数据，使 P0 用例 ``test_role_limited_layout_binding_takes_effect``
不再因数据缺失而跳过，真正执行 r349152（角色受范围限制权限绑定布局）的修复路径。

构建链路（由 E9 MCP 源码反查确认）：
``getLayoutList`` 取查看/编辑布局 → ``getRoleSetList`` 取角色 →
``doSubmit``（employee1）建一笔真实单据（创建人=该员工）→
``/hrm/roleset/save`` 把该员工加入角色 → ``saveModeRightList`` 保存
一条 sharetype=4 / isrolelimited=1 / rolefield=-101(创建人) 的受限权限，
绑定查看/编辑布局 → ``layoutBase`` 验证返回编辑布局。

用法（在 api-test/ 下）：
    python tools/prepare_formmode_test_data.py             # 构建并写入 test_data
    python tools/prepare_formmode_test_data.py --cleanup   # 回收权限规则/角色成员/单据

产物状态写入 ``test_data/formmode/formmode_test_data.json``——测试用例依赖的数据
属于交付物，纳入 Git 管理并按模块分目录（勿放 runtime/）；重复执行幂等复用。
本工具只使用管理员与测试员工账号在测试环境创建可回收数据，不读取或输出任何凭据。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from page_api.login_api.login_api import LoginAPI  # noqa: E402
from page_api.public.api_context import APIContext  # noqa: E402
from page_api.public.base_api import BaseAPI  # noqa: E402
from utils.common_function import load_account  # noqa: E402

# 已实测可用的目标模块/表单（E9 环境固定值，见探针 v7 结论）。
MODE_ID = "1001"
FORM_ID = "-7"
# 角色受范围限制权限参数：sharetype=4(角色)、isrolelimited=1(受范围限制)、
# rolefieldtype=1(人员字段)、rolefield1=-101(创建人)、rolelevel=2(总部)、righttype=2(编辑)。
RIGHTTYPE_SHARE = "3"  # 顶层权限类别：3 共享
SHARETYPE_ROLE = "4"   # 共享对象：角色
ROLE_FIELD_TYPE = "1"  # 人员字段
ROLE_FIELD = "-101"    # 模块创建人
ROLE_LEVEL = "2"       # 总部
RIGHT_TYPE_EDIT = "2"  # 编辑权限
STATE_PATH = PROJECT_ROOT / "test_data" / "formmode" / "formmode_test_data.json"


def log(message: str) -> None:
    print(f"[r349152-prep] {message}")


def fail(message: str) -> int:
    print(f"[r349152-prep] 失败：{message}", file=sys.stderr)
    return 1


def login(role: str) -> tuple[APIContext, dict]:
    """按框架 fixture 同样的方式登录指定账号，返回 (共享会话上下文, 登录响应)。"""
    account = load_account(role)
    if not account.get("user_name") or not account.get("password"):
        raise RuntimeError(f"账号 {role} 未配置（config.json 或 test_data/account.json）")
    api = LoginAPI()
    api._caller = account["user_name"]
    api.get_rsa_info()
    response = api.check_login(
        loginid=account["user_name"],
        userpassword=account["password"],
    )
    if response.get("msgcode") != "0" or response.get("loginstatus") != "true":
        raise RuntimeError(f"{role} 登录失败: {LoginAPI.safe_login_fields(response)}")
    api.remind_login()
    api.is_weak_password(password=account["password"])
    api.get_os_info()
    return APIContext(api, caller=account["user_name"]), response


def load_state() -> dict:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def table_datas(api: BaseAPI, sessionkey: str) -> list:
    """E9 分页表：通过 sessionkey 取 table/datas 的真实数据行。"""
    if not sessionkey:
        return []
    rd = api.post("/api/ec/dev/table/datas", data={"dataKey": sessionkey})
    datas = (rd or {}).get("datas") if isinstance(rd, dict) else None
    return datas if isinstance(datas, list) else []


def resolve_layouts(admin: BaseAPI) -> tuple[str, str]:
    """取 mode 的查看布局与编辑布局 id，返回 (view_id, edit_id)。"""
    rl = admin.post("/api/cube/mode/mode/getLayoutList", data={"modeid": MODE_ID})
    layouts = table_datas(admin, (rl or {}).get("sessionkey")) if isinstance(rl, dict) else []
    view = next((d for d in layouts if str(d.get("type")) == "0"), None)
    edit = next((d for d in layouts if str(d.get("type")) == "2"), None)
    view_id = str(view.get("ID") or view.get("id") or "") if view else ""
    edit_id = str(edit.get("ID") or edit.get("id") or "") if edit else ""
    if not view_id or not edit_id:
        raise RuntimeError(f"mode {MODE_ID} 未取到查看/编辑布局（view={view_id} edit={edit_id}）")
    return view_id, edit_id


def resolve_role(admin: BaseAPI) -> tuple[str, str]:
    """取第一个可用角色，返回 (role_id, role_mark)。"""
    r_role = admin.post("/api/hrm/role/getRoleSetList", data={})
    roles = table_datas(admin, (r_role or {}).get("sessionkey")) if isinstance(r_role, dict) else []
    if not roles:
        raise RuntimeError("环境中无可用角色")
    first = roles[0]
    role_id = str(first.get("id") or first.get("ID") or "")
    role_mark = str(first.get("rolesmark") or first.get("rolesmark") or "")
    if not role_id:
        raise RuntimeError("角色列表未返回 id")
    return role_id, role_mark


def create_bill(emp_ctx: APIContext) -> str:
    """employee1 建一笔真实单据，返回 billid（创建人为该员工）。"""
    emp = emp_ctx.use(BaseAPI)
    submit = {
        "modeId": MODE_ID,
        "formId": FORM_ID,
        "billid": "0",
        "type": "1",
        "src": "save",
        "iscreate": "1",
        "JSONStr": "{}",
        "isMultiDoc": "",
    }
    rr = emp.post("/api/formmode/card/doSubmit", data=submit, status_code=0, return_response=True)
    try:
        body = rr.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict) or body.get("api_status") is not True:
        raise RuntimeError(f"doSubmit 建单失败: {rr.text[:500]}")
    billid = str(body.get("billid") or "")
    if not billid or billid == "0":
        raise RuntimeError(f"doSubmit 未返回有效 billid: {rr.text[:500]}")
    return billid


def add_role_member(admin: BaseAPI, role_id: str, member_uid: str) -> None:
    """把成员加入角色（upsert，重复执行安全）。"""
    resp = admin.post(
        "/api/hrm/roleset/save",
        data={"rolesid": role_id, "id": member_uid, "rolelevel": ROLE_LEVEL},
    )
    if not isinstance(resp, dict) or str(resp.get("status")) != "1":
        raise RuntimeError(f"加角色成员失败: {resp}")


def save_role_limited_right(
    admin: BaseAPI, role_id: str, view_id: str, edit_id: str
) -> dict:
    """保存一条角色受范围限制权限，返回响应（status=1 表示成功）。"""
    save_right = {
        "operation": "saveModeRight",
        "modeid": MODE_ID,
        "righttype": RIGHTTYPE_SHARE,
        "dataLength": "1",
        "sharetype_0": SHARETYPE_ROLE,
        "relatedid4_0": role_id,
        "rolelevel_0": ROLE_LEVEL,
        "showlevel_0": "0",
        "showlevel2_0": "9999",
        "righttype_0": RIGHT_TYPE_EDIT,
        "layoutid_0": view_id,
        "layoutid1_0": edit_id,
        "layoutorder_0": "1",
        "isRoleLimited_0": "1",
        "rolefieldtype_0": ROLE_FIELD_TYPE,
        "rolefield1_0": ROLE_FIELD,
    }
    resp = admin.post("/api/cube/mode/mode/saveModeRightList", data=save_right)
    if not isinstance(resp, dict) or str(resp.get("status")) != "1":
        raise RuntimeError(f"保存受限权限失败: {resp}")
    return resp


def find_right_ids(admin: BaseAPI, role_id: str) -> list[str]:
    """回读与该角色相关的全部受限权限规则 id（cleanup 用，可能含历史残留重复项）。"""
    resp = admin.get(
        "/api/cube/mode/mode/getModeRightList",
        params={
            "operation": "getModeRightList",
            "modeid": MODE_ID,
            "righttype": RIGHTTYPE_SHARE,
            "loadAllData": "0",
        },
    )
    if not isinstance(resp, dict):
        return []
    right_info = resp.get("rightListInfo") or {}
    if not isinstance(right_info, dict):
        return []
    matched: list[str] = []
    for list_key in ("editRightList", "controlRightList", "viewRightList", "addRightList"):
        rows = right_info.get(list_key) or []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            if str(row.get("isrolelimited")) == "1" and str(row.get("relatedid")) == role_id:
                right_id = str(row.get("rightId") or "")
                if right_id and right_id not in matched:
                    matched.append(right_id)
    return matched


def find_member_id(admin: BaseAPI, member_uid: str, role_id: str) -> str:
    """回读角色成员记录 id（cleanup 用）。"""
    resp = admin.post("/api/hrm/roleset/getSearchResult", data={"id": member_uid})
    rows = table_datas(admin, (resp or {}).get("sessionkey")) if isinstance(resp, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("roleid")) == role_id:
            return str(row.get("id") or "")
    return ""


def delete_right(admin: BaseAPI, right_ids: list[str]) -> int:
    """删除多条权限规则（逗号连接），返回成功删除的批次数。"""
    ids = [i for i in right_ids if i]
    if not ids:
        return 0
    resp = admin.post(
        "/api/cube/mode/mode/saveModeRightList",
        data={"operation": "delRight", "modeid": MODE_ID, "ids": ",".join(ids), "deleteData": "0"},
    )
    return len(ids) if (isinstance(resp, dict) and str(resp.get("status")) == "1") else 0


def delete_role_member(admin: BaseAPI, member_id: str) -> bool:
    if not member_id:
        return False
    resp = admin.post("/api/hrm/roleset/delete", data={"id": member_id})
    return isinstance(resp, dict) and str(resp.get("status")) == "1"


def delete_bill(emp_ctx: APIContext, billid: str) -> bool:
    if not billid:
        return False
    emp = emp_ctx.use(BaseAPI)
    resp = emp.post(
        "/api/formmode/card/doDel",
        data={"modeId": MODE_ID, "formId": FORM_ID, "billid": billid},
    )
    return isinstance(resp, dict) and resp.get("api_status") is True


def verify_layout(emp_ctx: APIContext, billid: str) -> tuple[str, str]:
    """employee1 验证编辑布局返回，返回 (actual_layoutid, api_status)。"""
    emp = emp_ctx.use(BaseAPI)
    resp = emp.post(
        "/api/formmode/card/layoutBase",
        data={"modeId": MODE_ID, "formId": FORM_ID, "type": "2", "billid": billid, "JSONStr": "{}"},
    )
    if not isinstance(resp, dict):
        return "", "False"
    return str(resp.get("layoutid") or ""), str(resp.get("api_status") or "")


def cleanup(state: dict, admin_ctx: APIContext, emp_ctx: APIContext) -> None:
    """回收权限规则、角色成员与单据（尽力而为，不因单步失败中断）。"""
    admin = admin_ctx.use(BaseAPI)
    role_id = str(state.get("_role_id") or "")
    right_ids = [i for i in str(state.get("_right_ids") or "").split(",") if i]
    if role_id:
        live_ids = find_right_ids(admin, role_id)
        for i in live_ids:
            if i not in right_ids:
                right_ids.append(i)
    member_id = str(state.get("_member_id") or "")
    billid = str(state.get("role_limited_billid") or "")

    try:
        deleted = delete_right(admin, right_ids)
        if deleted:
            log(f"已删除权限规则 {right_ids}")
        else:
            log(f"权限规则未删除或未定位（right_ids={right_ids or '空'}）")
    except Exception as exc:  # noqa: BLE001
        log(f"删除权限规则异常：{exc}")

    try:
        if delete_role_member(admin, member_id):
            log(f"已删除角色成员记录 {member_id}")
        elif member_id:
            log(f"角色成员记录未删除（member_id={member_id}）")
    except Exception as exc:  # noqa: BLE001
        log(f"删除角色成员异常：{exc}")

    try:
        if delete_bill(emp_ctx, billid):
            log(f"已删除单据 {billid}")
        elif billid:
            log(f"单据未删除（billid={billid}）")
    except Exception as exc:  # noqa: BLE001
        log(f"删除单据异常：{exc}")

    # 清空数据基线中的运行时字段，保留静态说明字段与模块骨架。
    base = load_state()
    for key in (
        "mode_id", "form_id", "billid",
        "role_limited_mode_id", "role_limited_form_id",
        "role_limited_billid", "role_limited_expected_layoutid",
        "_right_ids", "_member_id", "_role_id", "_employee_uid", "_view_layout", "_edit_layout",
    ):
        base[key] = ""
    save_state(base)
    log("已清空数据基线中的运行时字段")


def build(admin_ctx: APIContext, emp_ctx: APIContext, member_uid: str) -> dict:
    """幂等构建：若已有可用状态则复用，否则重建一组数据。"""
    admin = admin_ctx.use(BaseAPI)
    state = load_state()

    # 已有状态且单据仍可解析出编辑布局 → 幂等复用。
    existing_billid = str(state.get("role_limited_billid") or "")
    if existing_billid and existing_billid.isdigit():
        actual, api_status = verify_layout(emp_ctx, existing_billid)
        if api_status == "True" and actual:
            log(f"检测到已有可用构建状态，幂等复用（billid={existing_billid}，实际布局 {actual}）")
            return state

    # 重建：先回收旧的运行时数据（如存在），再全新构建。
    if state.get("_right_ids") or state.get("_member_id") or existing_billid:
        log("检测到旧的构建状态但已失效，先回收再重建")
        cleanup(state, admin_ctx, emp_ctx)
        state = load_state()

    view_id, edit_id = resolve_layouts(admin)
    log(f"布局：查看 {view_id} / 编辑 {edit_id}")

    role_id, role_mark = resolve_role(admin)
    log(f"角色：{role_mark or role_id}（id={role_id}）")

    billid = create_bill(emp_ctx)
    log(f"employee1 建单成功：billid={billid}")

    add_role_member(admin, role_id, member_uid)
    log(f"已把 employee1（uid={member_uid}）加入角色 {role_id}")

    save_role_limited_right(admin, role_id, view_id, edit_id)
    log("已保存角色受范围限制权限（sharetype=4/isrolelimited=1/rolefield=-101/编辑布局）")

    right_ids = find_right_ids(admin, role_id)
    member_id = find_member_id(admin, member_uid, role_id)
    actual, api_status = verify_layout(emp_ctx, billid)
    log(f"layoutBase 验证：api_status={api_status}，实际编辑布局 {actual}")

    new_state = {
        **state,
        "mode_id": MODE_ID,
        "form_id": FORM_ID,
        "billid": billid,
        "role_limited_mode_id": MODE_ID,
        "role_limited_form_id": FORM_ID,
        "role_limited_billid": billid,
        "role_limited_expected_layoutid": edit_id,
        "_right_ids": ",".join(right_ids),
        "_member_id": member_id,
        "_role_id": role_id,
        "_employee_uid": member_uid,
        "_view_layout": view_id,
        "_edit_layout": edit_id,
    }
    save_state(new_state)
    return new_state


def main() -> int:
    parser = argparse.ArgumentParser(description="r349152 阶段 C 表单建模前置数据准备")
    parser.add_argument("--cleanup", action="store_true", help="回收权限规则/角色成员/单据后退出")
    args = parser.parse_args()

    try:
        admin_ctx, _admin_resp = login("admin")
        emp_ctx, emp_resp = login("employee1")
    except Exception as exc:  # noqa: BLE001
        return fail(f"登录失败：{exc}")
    log("管理员与员工登录成功")

    member_uid = str((emp_resp or {}).get("userid") or "")
    if not member_uid:
        return fail("employee1 登录响应缺少 userid，无法定位成员 uid")

    state = load_state()
    if args.cleanup:
        cleanup(state, admin_ctx, emp_ctx)
        return 0

    try:
        state = build(admin_ctx, emp_ctx, member_uid)
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))

    print()
    print("=== r349152 前置数据已就绪（写入 test_data/formmode/formmode_test_data.json）===")
    print(f"E9_R349152_ROLE_LIMITED_MODE_ID={state.get('role_limited_mode_id', '')}")
    print(f"E9_R349152_ROLE_LIMITED_FORM_ID={state.get('role_limited_form_id', '')}")
    print(f"E9_R349152_ROLE_LIMITED_BILLID={state.get('role_limited_billid', '')}")
    print(f"E9_R349152_ROLE_LIMITED_EXPECTED_LAYOUTID={state.get('role_limited_expected_layoutid', '')}")
    print()
    log("完成：可执行 python runpytest.py -m r349152 --no-clean 复测")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
