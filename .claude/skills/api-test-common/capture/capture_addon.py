# -*- coding: utf-8 -*-

"""api-test-common mitmdump addon.

抓取 `config.base_url` 对应站点的接口请求，落盘到 `runtime/latest.jsonl`。
"""

import ast
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse


ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(ADDON_DIR)
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from mitmproxy import ctx, http  # noqa: E402

from skill_utils.common_function import update_skill_config  # noqa: E402
from skill_utils.project_root import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    TEMP_DIR_NAME,
    resolve_project_root,
)


PREFIX_FILE = os.path.join(ADDON_DIR, "allowed_prefixes.txt")
BLOCKED_PREFIX_FILE = os.path.join(ADDON_DIR, "blocked_prefixes.txt")

STATIC_SUFFIX = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".map",
)
BINARY_CT_PREFIXES = (
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/x-zip",
    "application/x-rar",
    "application/x-7z",
    "application/x-tar",
    "application/x-gzip",
    "application/vnd.ms-",
    "application/vnd.openxmlformats-",
    "image/",
    "video/",
    "audio/",
)
MAX_BODY_BYTES = 1024 * 1024


def _warn(msg: str) -> None:
    ctx.log.warn(f"[api-test-common] {msg}")


def _info(msg: str) -> None:
    ctx.log.info(f"[api-test-common] {msg}")


def _resolve_repo_root() -> Optional[str]:
    return resolve_project_root(on_warn=_warn, on_info=_info)


def _get_jsonl_path() -> str:
    repo_root = _resolve_repo_root()
    if not repo_root:
        return os.path.join(ADDON_DIR, "latest.jsonl")
    runtime_dir = os.path.join(repo_root, TEMP_DIR_NAME)
    os.makedirs(runtime_dir, exist_ok=True)
    return os.path.join(runtime_dir, "latest.jsonl")


def _parse_base_url(config_path: str) -> str:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=config_path)
    except Exception as exc:
        _warn(f"解析 config.py 失败: {exc}")
        return ""

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "base_url":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value.strip()
    return ""


def _save_base_url_to_skill_config(base_url: str) -> None:
    if not base_url:
        return
    update_skill_config(
        {"base_url": base_url},
        config_path=DEFAULT_CONFIG_PATH,
        on_warn=_warn,
        on_info=_info,
    )


def _load_baseurl() -> str:
    repo_root = _resolve_repo_root()
    if not repo_root:
        return ""
    config_path = os.path.join(repo_root, "config.py")
    if not os.path.isfile(config_path):
        _warn(f"未找到 config.py: {config_path}")
        return ""
    base_url = _parse_base_url(config_path)
    if not base_url:
        _warn("未能从 config.py 读取 base_url，将不做 host 过滤")
        return ""
    _save_base_url_to_skill_config(base_url)
    return base_url


def _load_prefix_file(path: str, display_name: str) -> List[str]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f]
        return [line for line in lines if line and not line.startswith("#")]
    except Exception as exc:
        _warn(f"读取 {display_name} 失败: {exc}")
        return []


def _load_prefixes() -> List[str]:
    return _load_prefix_file(PREFIX_FILE, "allowed_prefixes.txt")


def _load_blocked_prefixes() -> List[str]:
    return _load_prefix_file(BLOCKED_PREFIX_FILE, "blocked_prefixes.txt")


def _digest(value: str, keep: int = 20) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return f"{value}|len={len(value)}"
    return f"{value[:keep]}...|len={len(value)}"


def _is_binary_ct(ct: str) -> bool:
    ct = (ct or "").lower()
    return any(ct.startswith(prefix) for prefix in BINARY_CT_PREFIXES)


def _looks_encoded_blob(body_bytes: bytes) -> bool:
    if len(body_bytes) <= 2048:
        return False
    try:
        text = body_bytes.decode("ascii")
    except UnicodeDecodeError:
        return False
    if re.fullmatch(r"[A-Za-z0-9+/=\s]+", text):
        return True
    if re.fullmatch(r"[0-9a-fA-F\s]+", text):
        return True
    if re.fullmatch(r"[0-9\s]+", text):
        return True
    return False


def _match_baseurl(host_port: str, baseurl: str) -> bool:
    if not baseurl:
        return True
    parsed = urlparse(baseurl)
    return host_port.lower() == parsed.netloc.lower()


class ApiCaptureAddon:
    def __init__(self):
        self.baseurl = _load_baseurl()
        self.prefixes = _load_prefixes()
        self.blocked_prefixes = _load_blocked_prefixes()
        self.jsonl_path = _get_jsonl_path()
        self._ensure_jsonl()
        ctx.log.info(f"[api-test-common] self.baseurl = {self.baseurl or '<empty>'}")
        ctx.log.info(f"[api-test-common] self.prefixes = {self.prefixes}")
        ctx.log.info(f"[api-test-common] self.blocked_prefixes = {self.blocked_prefixes}")
        ctx.log.info(f"[api-test-common] self.jsonl_path = {self.jsonl_path}")

    def _ensure_jsonl(self):
        if not os.path.isfile(self.jsonl_path):
            open(self.jsonl_path, "w", encoding="utf-8").close()

    def _should_capture(self, flow: http.HTTPFlow) -> bool:
        req = flow.request
        pure_path = (req.path or "/").split("?", 1)[0].lower()
        if pure_path.endswith(STATIC_SUFFIX):
            return False

        host_port = req.host
        if req.port and req.port not in (80, 443):
            host_port = f"{req.host}:{req.port}"
        if not _match_baseurl(host_port, self.baseurl):
            return False

        if self.prefixes and not any(pure_path.startswith(prefix) for prefix in self.prefixes):
            return False
        if self.blocked_prefixes and any(pure_path.startswith(prefix) for prefix in self.blocked_prefixes):
            return False
        return True

    def _build_record(self, flow: http.HTTPFlow) -> dict:
        req = flow.request
        resp = flow.response

        req_headers = {}
        for key, value in req.headers.items():
            if key.lower() in ("cookie", "authorization"):
                req_headers[key] = _digest(value)
            else:
                req_headers[key] = value

        try:
            req_body_text = req.get_text(strict=False) if req.content is not None else None
        except Exception:
            req_body_text = None

        body_skipped = False
        body_truncated = False
        skip_reason = ""
        resp_body_text = None
        resp_content_type = (resp.headers.get("content-type") or "") if resp else ""
        if resp is not None:
            raw = resp.raw_content or b""
            if _is_binary_ct(resp_content_type):
                body_skipped = True
                skip_reason = f"binary-content-type:{resp_content_type}"
                resp_body_text = f"<BINARY_SKIPPED: content-type={resp_content_type}, size={len(raw)}>"
            elif _looks_encoded_blob(raw):
                body_skipped = True
                skip_reason = "encoded-blob"
                resp_body_text = f"<ENCODED_SKIPPED: size={len(raw)}>"
            elif len(raw) > MAX_BODY_BYTES:
                body_truncated = True
                resp_body_text = raw[:MAX_BODY_BYTES].decode("utf-8", errors="replace")
            else:
                try:
                    resp_body_text = resp.get_text(strict=False)
                except Exception:
                    resp_body_text = None

        pure_path = (req.path or "/").split("?", 1)[0]
        host_port = req.host
        if req.port and req.port not in (80, 443):
            host_port = f"{req.host}:{req.port}"
        return {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "epoch": time.time(),
            "method": req.method,
            "scheme": req.scheme,
            "host": host_port,
            "path": req.path,
            "pure_path": pure_path,
            "url": req.url,
            "req_headers": req_headers,
            "req_body": req_body_text,
            "status": resp.status_code if resp else None,
            "resp_content_type": resp_content_type,
            "resp_body": resp_body_text,
            "body_skipped": body_skipped,
            "body_truncated": body_truncated,
            "skip_reason": skip_reason,
        }

    def response(self, flow: http.HTTPFlow):
        try:
            if not self._should_capture(flow):
                return
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(self._build_record(flow), ensure_ascii=False) + "\n")
        except Exception as exc:
            ctx.log.warn(f"[api-test-common] 落盘异常: {exc}")


addons = [ApiCaptureAddon()]
