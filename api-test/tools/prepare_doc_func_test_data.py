# -*- coding: utf-8 -*-
"""r349155 阶段 C 前置数据准备工具。

基于 E9 文档（采知连）后端 API 自动构建一条「含无后缀附件」的文档，
用于验证 r349155 修复：开启采知连非标后，文件夹/文档下载遇到无后缀文件
不再报「无下载文件」。

链路（由 E9 MCP 源码反查 + 实测确认）：
``登录管理员`` → ``/api/doc/upload/uploadFile2Doc`` 上传无后缀文件（生成文档 + 附件）
→ ``/api/yd/doc/func/generateDocZip`` 按 docIds / secCategoryIds 下载。
环境部署探测并入准备流程：构建后立即以 docIds 触发下载，
若返回 code=1 说明环境已部署修复；若返回 code=0 / 异常则记录环境可能未部署 r349155。

用法（在 api-test/ 下）：
    python tools/prepare_doc_func_test_data.py             # 构建并输出环境变量
    python tools/prepare_doc_func_test_data.py --cleanup   # 回收全部构建数据

产物状态写入 ``test_data/doc_func/doc_func_test_data.json``——测试用例依赖的数据
属于交付物，纳入 Git 管理并按模块分目录（勿放 runtime/）；重复执行幂等复用。
本工具只使用管理员账号在测试环境创建可回收数据，不读取或输出任何凭据。
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

from page_api.login_api.login_api import LoginAPI  # noqa: E402
from utils.common_function import load_account  # noqa: E402

STATE_PATH = PROJECT_ROOT / "test_data" / "doc_func" / "doc_func_test_data.json"
# 文档落点目录：default 目录（见文档目录树 key=1），上传与下载校验保持一致。
SEC_CATEGORY_ID = "1"
NOEXT_PREFIX = "E9R349155NOEXT"
MAX_DOWNLOAD_TIMEOUT = 90


def log(message: str) -> None:
    print(f"[r349155-prep] {message}")


def fail(message: str) -> int:
    print(f"[r349155-prep] 失败：{message}", file=sys.stderr)
    return 1


def load_state() -> dict:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def login_cookies() -> tuple[dict, str]:
    """按框架 fixture 同样的步骤登录管理员，返回 Cookie 字典与 base_url。"""
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
    return dict(api.get_base_request().cookies), api.base_url


def upload_noext_doc(base_url: str, cookies: dict, filename: str) -> dict:
    """上传一个无后缀文件并生成文档，返回其 docid 与 imagefileid。"""
    sess = requests.Session()
    files = {"file": (filename, b"e9 r349155 no-extension attachment probe", "application/octet-stream")}
    data = {"category": SEC_CATEGORY_ID, "docsubject": filename}
    response = sess.post(
        base_url + "/api/doc/upload/uploadFile2Doc",
        files=files,
        data=data,
        cookies=cookies,
        timeout=30,
        verify=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"上传无后缀文件 HTTP 异常: {response.status_code}")
    payload = response.json()
    data = payload.get("data") or {}
    docid = str(data.get("fileid") or "")
    imagefileid = str(data.get("imagefileid") or "")
    if not docid or not imagefileid:
        raise RuntimeError(f"上传无后缀文件未返回 docid/imagefileid: {payload}")
    return {"doc_id": docid, "imagefile_id": imagefileid, "noext_filename": filename}


def probe_download(base_url: str, cookies: dict, doc_id: str) -> dict:
    """用 docIds 触发单文件下载，探测环境是否已部署 r349155 修复。"""
    sess = requests.Session()
    response = sess.post(
        base_url + "/api/yd/doc/func/generateDocZip",
        data={"secCategoryIds": "", "docIds": doc_id},
        cookies=cookies,
        timeout=MAX_DOWNLOAD_TIMEOUT,
        verify=False,
    )
    try:
        payload = response.json()
    except ValueError:
        return {"code": -1, "raw": response.text[:200]}
    return {
        "code": payload.get("code"),
        "imageFileIds": bool(payload.get("imageFileIds")),
    }


def delete_doc(base_url: str, cookies: dict, doc_id: str) -> None:
    """回收构建的文档（进入回收站或直接删除）。"""
    sess = requests.Session()
    response = sess.get(
        base_url + "/api/doc/operate/delete",
        params={"docid": doc_id},
        cookies=cookies,
        timeout=20,
        verify=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"删除文档 {doc_id} 异常: {response.status_code}")


def cleanup(state: dict, base_url: str, cookies: dict) -> None:
    """回收构建的无后缀附件文档。"""
    doc_id = str(state.get("doc_id") or "")
    if doc_id:
        try:
            delete_doc(base_url, cookies, doc_id)
            log(f"已删除文档 {doc_id}")
        except Exception as exc:  # noqa: BLE001 — 清理尽量执行
            log(f"删除文档 {doc_id} 失败：{exc}")
    if STATE_PATH.exists():
        STATE_PATH.unlink()
        log("已删除状态文件")


def main() -> int:
    parser = argparse.ArgumentParser(description="r349155 阶段 C 前置数据准备")
    parser.add_argument("--cleanup", action="store_true", help="回收全部构建数据后退出")
    args = parser.parse_args()

    try:
        cookies, base_url = login_cookies()
    except Exception as exc:  # noqa: BLE001
        return fail(f"登录失败：{exc}")
    log("管理员登录成功")

    state = load_state()
    if args.cleanup:
        cleanup(state, base_url, cookies)
        return 0

    try:
        if state.get("doc_id") and state.get("imagefile_id"):
            log("检测到已有构建状态，幂等复用（如需重建请先 --cleanup）")
        else:
            filename = f"{NOEXT_PREFIX}{int(time.time()) % 1000000}"
            created = upload_noext_doc(base_url, cookies, filename)
            log(f"已创建含无后缀附件文档 docid={created['doc_id']} imagefileid={created['imagefile_id']}")
            state.update(created)

        # 环境部署探测：以 docIds 触发下载，检验无后缀附件是否仍被误判为「无下载文件」。
        probe = probe_download(base_url, cookies, state["doc_id"])
        env_fixed = probe.get("code") == 1
        state["env_deployed_fixed"] = env_fixed
        state["sec_category_id"] = SEC_CATEGORY_ID
        save_state(state)

        if env_fixed:
            log("环境部署探测：generateDocZip 对无后缀附件返回 code=1，环境已部署 r349155 修复。")
        else:
            log(f"环境部署探测：generateDocZip 返回 {probe}，环境可能尚未部署 r349155，测试执行时按版本差异假设处理。")
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc))

    print()
    print(f"E9_R349155_DOC_ID={state.get('doc_id', '')}")
    print(f"E9_R349155_IMAGE_FILE_ID={state.get('imagefile_id', '')}")
    print(f"E9_R349155_SEC_CATEGORY_ID={state.get('sec_category_id', '')}")
    print()
    log("完成：以上环境变量可直接用于 python runpytest.py -m r349155 --clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
