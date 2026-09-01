# -*- coding: utf-8 -*-
"""E9 MCP 调用方客户端。

本仓库不启动本地图谱运行时，也不读取本地 ``code_repo``。
图谱由外部 E9 MCP 服务（codebase-memory）维护；本模块只通过 HTTP Streamable HTTP
完成 initialize、会话管理和 tools/call。
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import requests


PROTOCOL_VERSION = "2025-03-26"
GRAPH_PROJECT = "e9"


class McpError(RuntimeError):
    """远端 MCP 服务不可用、认证失败或查询失败。"""


@dataclass(frozen=True)
class RemoteMcpConfig:
    """远端 MCP 网关连接配置；凭据只从运行环境读取。"""

    url: str
    version: str
    token: str
    verify: str | bool = True
    cert: tuple[str, str] | str | None = None
    timeout: float = 120.0

    @classmethod
    def from_environment(cls) -> "RemoteMcpConfig":
        """读取并严格校验查询 MCP 配置；企业网关要求 HTTPS + Bearer。"""
        url = os.environ.get("E9_MCP_URL", "").strip()
        if not url:
            raise McpError("未配置 E9_MCP_URL；本仓库只支持调用外部 MCP")
        if not url.lower().startswith("https://"):
            raise McpError("远端 MCP 必须使用 HTTPS")
        version = os.environ.get("E9_MCP_VERSION", "").strip()
        if not version:
            raise McpError("远端 MCP 未配置 E9_MCP_VERSION")
        token = os.environ.get("E9_MCP_TOKEN", "").strip()
        token_file = os.environ.get("E9_MCP_TOKEN_FILE", "").strip()
        if not token and token_file:
            try:
                token = Path(token_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise McpError("远端 MCP token 文件不可读") from exc
        if not token:
            raise McpError("远端 MCP 未配置 Bearer token")
        ca_bundle = os.environ.get("E9_MCP_CA_BUNDLE", "").strip()
        verify: str | bool = ca_bundle or True
        client_cert = os.environ.get("E9_MCP_CLIENT_CERT", "").strip()
        client_key = os.environ.get("E9_MCP_CLIENT_KEY", "").strip()
        if bool(client_cert) != bool(client_key):
            raise McpError("远端 MCP mTLS 必须同时配置客户端证书和私钥")
        cert: tuple[str, str] | None = (client_cert, client_key) if client_cert else None
        try:
            timeout = float(os.environ.get("E9_MCP_TIMEOUT", "120"))
        except ValueError as exc:
            raise McpError("远端 MCP 超时必须为数字") from exc
        if timeout <= 0:
            raise McpError("远端 MCP 超时必须大于 0")
        return cls(url=url, version=version, token=token, verify=verify, cert=cert, timeout=timeout)

    @classmethod
    def from_ops_environment(cls) -> "RemoteMcpConfig":
        """运维 MCP（e9-ops）配置。现网局域网允许 HTTP，Bearer 可选。"""
        url = os.environ.get("E9_OPS_MCP_URL", "").strip()
        if not url:
            raise McpError("未配置 E9_OPS_MCP_URL")
        token = os.environ.get("E9_OPS_MCP_TOKEN", "").strip() or os.environ.get("E9_MCP_TOKEN", "").strip()
        token_file = os.environ.get("E9_MCP_TOKEN_FILE", "").strip()
        if not token and token_file:
            try:
                token = Path(token_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise McpError("远端 MCP token 文件不可读") from exc
        ca_bundle = os.environ.get("E9_MCP_CA_BUNDLE", "").strip()
        verify: str | bool = ca_bundle or True
        client_cert = os.environ.get("E9_MCP_CLIENT_CERT", "").strip()
        client_key = os.environ.get("E9_MCP_CLIENT_KEY", "").strip()
        if bool(client_cert) != bool(client_key):
            raise McpError("远端 MCP mTLS 必须同时配置客户端证书和私钥")
        cert: tuple[str, str] | None = (client_cert, client_key) if client_cert else None
        try:
            timeout = float(os.environ.get("E9_OPS_MCP_TIMEOUT", os.environ.get("E9_MCP_TIMEOUT", "90")))
        except ValueError as exc:
            raise McpError("远端 MCP 超时必须为数字") from exc
        if timeout <= 0:
            raise McpError("远端 MCP 超时必须大于 0")
        version = os.environ.get("E9_MCP_VERSION", "").strip()
        return cls(url=url, version=version, token=token, verify=verify, cert=cert, timeout=timeout)


class RemoteMcpSession:
    """通过 HTTP Streamable HTTP 调用外部 E9 MCP 服务。"""

    def __init__(self, config: RemoteMcpConfig) -> None:
        self.config = config
        self.session = requests.Session()
        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }
        if config.token:
            headers["authorization"] = f"Bearer {config.token}"
        self.session.headers.update(headers)
        self.session_id = ""
        self._next_id = 0
        self._lock = threading.Lock()
        self._initialize()

    def _post(self, payload: dict[str, Any], *, notification: bool = False) -> requests.Response:
        headers = {"mcp-protocol-version": PROTOCOL_VERSION}
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        try:
            response = self.session.post(
                self.config.url,
                json=payload,
                headers=headers,
                verify=self.config.verify,
                cert=self.config.cert,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise McpError(f"远端 MCP HTTP 请求失败: {type(exc).__name__}") from exc
        return response

    def _initialize(self) -> None:
        with self._lock:
            self._next_id += 1
            response = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "svn-analyse", "version": "4.0"},
                    },
                }
            )
            self.session_id = response.headers.get("mcp-session-id", "")
            if not self.session_id:
                raise McpError("远端 MCP 初始化未返回 mcp-session-id")
            try:
                result = response.json().get("result", {})
            except ValueError as exc:
                raise McpError("远端 MCP 初始化响应不是 JSON") from exc
            negotiated = str(result.get("protocolVersion") or "")
            if negotiated not in {PROTOCOL_VERSION, "2024-11-05", "2025-03-26"}:
                raise McpError("远端 MCP 协议版本不匹配")
            self._post(
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                notification=True,
            )

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """调用外部工具并返回 MCP 文本内容。"""
        with self._lock:
            self._next_id += 1
            response = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise McpError("远端 MCP 工具响应不是 JSON") from exc
        if "error" in payload:
            error = payload["error"] or {}
            raise McpError(f"远端 MCP 工具调用失败: {error.get('message') or 'unknown_error'}")
        result = payload.get("result") or {}
        if result.get("isError"):
            raise McpError(f"远端 MCP 工具 {name} 执行失败: {_content_text(result)}")
        return _content_text(result)

    def close(self) -> None:
        """关闭 HTTP 会话并尽力回收远端 MCP session。"""
        try:
            if self.session_id:
                self.session.delete(
                    self.config.url,
                    headers={"mcp-session-id": self.session_id, "mcp-protocol-version": PROTOCOL_VERSION},
                    verify=self.config.verify,
                    cert=self.config.cert,
                    timeout=self.config.timeout,
                )
        except requests.RequestException:
            pass
        finally:
            self.session.close()


def _content_text(result: dict[str, Any]) -> str:
    """拼接 MCP 结果中的 content[*].text。"""
    parts: list[str] = []
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return "\n".join(parts)


_sessions: dict[str, RemoteMcpSession] = {}
_sessions_lock = threading.Lock()


def _session_key(config: RemoteMcpConfig) -> str:
    """生成不包含明文 Token 的会话缓存键。"""
    fingerprint = hashlib.sha256(config.token.encode("utf-8")).hexdigest()[:16]
    return f"{config.url}|{config.version}|{fingerprint}"


def get_session(_project_path: str | Path | None = None, timeout: int = 120) -> RemoteMcpSession:
    """获取远端会话；project_path 仅为兼容旧调用方而保留，不会被发送。"""
    config = RemoteMcpConfig.from_environment()
    if timeout != 120:
        config = replace(config, timeout=float(timeout))
    key = _session_key(config)
    with _sessions_lock:
        session = _sessions.get(key)
        if session is None:
            session = RemoteMcpSession(config)
            _sessions[key] = session
        return session


def close_all_sessions() -> None:
    """关闭全部远端会话。"""
    with _sessions_lock:
        sessions = list(_sessions.values())
        _sessions.clear()
    for session in sessions:
        session.close()


atexit.register(close_all_sessions)


def _mismatch_prefix(requested: str | None, current: str) -> str:
    if requested and current and requested != current:
        return json.dumps(
            {
                "warning": "graph_revision_mismatch",
                "requested": requested,
                "graph_version": current,
            },
            ensure_ascii=False,
        )
    return ""


def callers(_project_path: str | Path, symbol: str, version: str | None = None) -> str:
    """现网 CBM 无 callers 工具。改为 ``trace_path(inbound)``。"""
    config = RemoteMcpConfig.from_environment()
    prefix = _mismatch_prefix(version, config.version)
    text = _get_session_for_config(config).call_tool(
        "trace_path",
        {
            "project": GRAPH_PROJECT,
            "function_name": symbol,
            "direction": "inbound",
            "depth": 3,
        },
    )
    return f"{prefix}\n{text}".strip() if prefix else text


def impact(_project_path: str | Path, symbol: str, version: str | None = None) -> str:
    """现网 CBM 无 impact 工具。用 inbound 调用链近似影响规模。"""
    return callers(_project_path, symbol, version=version)


def svn_log(revision: str | int) -> dict[str, Any]:
    """调用运维 MCP ``e9_svn_log``，返回结构化提交信息。"""
    return _require_ops_ok(
        _get_session_for_config(RemoteMcpConfig.from_ops_environment()).call_tool(
            "e9_svn_log",
            {"revision": revision},
        )
    )


def svn_diff(revision: str | int, max_bytes: int = 262144) -> dict[str, Any]:
    """调用运维 MCP ``e9_svn_diff``，返回 unified diff。"""
    return _require_ops_ok(
        _get_session_for_config(RemoteMcpConfig.from_ops_environment()).call_tool(
            "e9_svn_diff",
            {"revision": revision, "max_bytes": max_bytes},
        )
    )


def _parse_ops_payload(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise McpError("运维 MCP 返回的不是 JSON") from exc
    if not isinstance(payload, dict):
        raise McpError("运维 MCP JSON 不是对象")
    return payload


def _require_ops_ok(text: str) -> dict[str, Any]:
    payload = _parse_ops_payload(text)
    if not payload.get("ok"):
        raise McpError(str(payload.get("error") or payload.get("message") or "e9_ops_failed"))
    return payload


def _get_session_for_config(config: RemoteMcpConfig) -> RemoteMcpSession:
    """按显式配置复用远端会话。"""
    key = _session_key(config)
    with _sessions_lock:
        session = _sessions.get(key)
        if session is None:
            session = RemoteMcpSession(config)
            _sessions[key] = session
        return session


# ── 五期：Revision 邻域查询 ────────────────────────────────────────


def list_revisions(revision: str | int, before: int = 10, after: int = 10) -> dict[str, Any]:
    """调用运维 MCP ``e9_list_revisions``。锚点不存在时返回 ``ok=false``，不抛异常。

    现网不在 codebase-memory 上提供该工具；请配置 ``E9_OPS_MCP_URL``。
    """
    try:
        text = _get_session_for_config(RemoteMcpConfig.from_ops_environment()).call_tool(
            "e9_list_revisions",
            {"revision": revision, "before": before, "after": after},
        )
        return _parse_ops_payload(text)
    except McpError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"list_revisions 调用失败: {exc}"}


def list_revisions_in_range(from_revision: str | int, to_revision: str | int) -> dict[str, Any]:
    """调用运维 MCP ``e9_list_revisions_in_range``。查询成功但区间不完整时 ``complete=false``。"""
    try:
        text = _get_session_for_config(RemoteMcpConfig.from_ops_environment()).call_tool(
            "e9_list_revisions_in_range",
            {"from_revision": from_revision, "to_revision": to_revision},
        )
        return _parse_ops_payload(text)
    except McpError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"list_revisions_in_range 调用失败: {exc}"}


# ── 从原 codegraph_ops 合并的解析函数 ──────────────────────────────


def parse_impact_size(stdout: str) -> int | None:
    """从 MCP impact / trace_path 文本中尽量抽出关联规模。"""
    if not stdout:
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        for key in ("callers_total", "impact_size", "size"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
        callers_list = payload.get("callers")
        if isinstance(callers_list, list):
            return len(callers_list)
    for pattern in (
        r"(\d+)\s*个关联",
        r"impact(?:\s*size)?\s*[:=]\s*(\d+)",
        r"(\d+)\s+related",
    ):
        match = re.search(pattern, stdout, re.I)
        if match:
            return int(match.group(1))
    return None


def extract_action_refs(text: str) -> list[dict[str, str]]:
    """从 callers/impact 文本中抓取入口类方法引用（XxxAction/Controller/Resource.method）。

    四期 T4.1：E9 入口类既有旧式 ``*Action``（com.api.*.web）也有新式
    ``*Controller``（com.api.*.controller），个别 ``*Resource``；三类后缀都要捕获。
    """
    if not text:
        return []
    seen: set[tuple[str, str]] = set()
    refs: list[dict[str, str]] = []
    for match in re.finditer(r"\b(\w+(?:Action|Controller|Resource))\.(\w+)\b", text):
        key = (match.group(1), match.group(2))
        if key in seen:
            continue
        seen.add(key)
        refs.append({"action": key[0], "method": key[1]})
    return refs