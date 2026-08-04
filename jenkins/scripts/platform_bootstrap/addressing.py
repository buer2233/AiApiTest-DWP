"""根据 Stage15 最小公共配置派生平台公开地址。"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Mapping

from .configuration import ConfigError


PUBLIC_ADDRESS_KEYS = (
    "PLATFORM_PUBLIC_HOST",
    "PLATFORM_PUBLIC_SCHEME",
    "MYSQL_HOST_PORT",
    "JENKINS_HTTP_PORT",
    "BACKEND_HOST_PORT",
    "FRONTEND_HOST_PORT",
)
HOST_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


@dataclass(frozen=True)
class PlatformPublicAddresses:
    jenkins: str
    mysql: str
    backend: str
    backend_api: str
    frontend: str


def _required(config: Mapping[str, str], key: str) -> str:
    value = str(config.get(key, "")).strip()
    if not value:
        raise ConfigError(f"required configuration key missing: {key}")
    return value


def _port(config: Mapping[str, str], key: str) -> int:
    raw = _required(config, key)
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"configuration key must be a valid port: {key}") from None
    if not 1 <= value <= 65535:
        raise ConfigError(f"configuration key must be a valid port: {key}")
    return value


def normalize_public_host(raw_host: str) -> str:
    """规范化 DNS/IPv4/IPv6 主机，拒绝端口、路径和 URL 分隔符。"""
    host = raw_host.strip()
    bracketed = host.startswith("[") or host.endswith("]")
    if bracketed:
        if not (host.startswith("[") and host.endswith("]")):
            raise ConfigError("configuration key must contain only a host: PLATFORM_PUBLIC_HOST")
        host = host[1:-1]
    if not host or any(character.isspace() for character in host):
        raise ConfigError("configuration key must contain only a host: PLATFORM_PUBLIC_HOST")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if bracketed or len(host) > 253 or any(
            not HOST_LABEL_PATTERN.fullmatch(label) for label in host.split(".")
        ):
            raise ConfigError("configuration key must contain only a host: PLATFORM_PUBLIC_HOST") from None
    return host


def format_url_host(host: str) -> str:
    """为 URL/host:port 输出格式化主机，IPv6 仅增加一层方括号。"""
    normalized = normalize_public_host(host)
    return f"[{normalized}]" if ":" in normalized else normalized


def _bounded_integer(
    config: Mapping[str, str],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = _required(config, key)
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"configuration key must be an integer: {key}") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"configuration key is outside the allowed range: {key}")
    return value


def validate_deployment_config(config: Mapping[str, str]) -> None:
    """在任何 Docker 命令前校验全部保留公共配置的类型与基础格式。"""
    derive_public_addresses(config)
    bind_host = _required(config, "PLATFORM_BIND_HOST")
    try:
        ipaddress.ip_address(bind_host)
    except ValueError:
        raise ConfigError("configuration key must be an IPv4 or IPv6 address: PLATFORM_BIND_HOST") from None
    _port(config, "JENKINS_AGENT_PORT")
    _bounded_integer(config, "DOCKER_GID", minimum=0, maximum=2_147_483_647)
    _bounded_integer(config, "CI_RUN_RETENTION_DAYS", minimum=1, maximum=3_650)
    _required(config, "PROJECT_WORKSPACE")
    image = _required(config, "FRONTEND_PLAYWRIGHT_BASE_IMAGE")
    if any(character.isspace() for character in image) or "://" in image or image.startswith("-"):
        raise ConfigError(
            "configuration key must be a Docker image reference: FRONTEND_PLAYWRIGHT_BASE_IMAGE"
        )


def derive_public_addresses(config: Mapping[str, str]) -> PlatformPublicAddresses:
    """派生外部入口；异常消息只包含配置键名，不包含赋值。"""
    host = normalize_public_host(_required(config, "PLATFORM_PUBLIC_HOST"))
    scheme = _required(config, "PLATFORM_PUBLIC_SCHEME").lower()
    if scheme not in {"http", "https"}:
        raise ConfigError("configuration key must be http or https: PLATFORM_PUBLIC_SCHEME")

    host_for_url = format_url_host(host)
    mysql_port = _port(config, "MYSQL_HOST_PORT")
    jenkins_port = _port(config, "JENKINS_HTTP_PORT")
    backend_port = _port(config, "BACKEND_HOST_PORT")
    frontend_port = _port(config, "FRONTEND_HOST_PORT")
    backend = f"{scheme}://{host_for_url}:{backend_port}"
    return PlatformPublicAddresses(
        jenkins=f"{scheme}://{host_for_url}:{jenkins_port}",
        mysql=f"{host_for_url}:{mysql_port}",
        backend=backend,
        backend_api=f"{backend}/api/v1",
        frontend=f"{scheme}://{host_for_url}:{frontend_port}",
    )
