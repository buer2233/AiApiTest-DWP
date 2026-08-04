"""Stage15 平台公开地址派生契约。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.addressing import derive_public_addresses  # noqa: E402
from platform_bootstrap.configuration import ConfigError  # noqa: E402


def test_public_addresses_share_host_scheme_and_use_service_ports() -> None:
    addresses = derive_public_addresses(
        {
            "PLATFORM_PUBLIC_HOST": "platform.example.test",
            "PLATFORM_PUBLIC_SCHEME": "https",
            "MYSQL_HOST_PORT": "13307",
            "JENKINS_HTTP_PORT": "18080",
            "BACKEND_HOST_PORT": "18000",
            "FRONTEND_HOST_PORT": "15173",
        }
    )

    assert addresses.jenkins == "https://platform.example.test:18080"
    assert addresses.mysql == "platform.example.test:13307"
    assert addresses.backend == "https://platform.example.test:18000"
    assert addresses.backend_api == "https://platform.example.test:18000/api/v1"
    assert addresses.frontend == "https://platform.example.test:15173"


@pytest.mark.parametrize("host", ["2001:db8::1", "[2001:db8::1]"])
def test_ipv6_public_host_is_normalized_and_bracketed_consistently(host: str) -> None:
    addresses = derive_public_addresses(
        {
            "PLATFORM_PUBLIC_HOST": host,
            "PLATFORM_PUBLIC_SCHEME": "https",
            "MYSQL_HOST_PORT": "13307",
            "JENKINS_HTTP_PORT": "18080",
            "BACKEND_HOST_PORT": "18000",
            "FRONTEND_HOST_PORT": "15173",
        }
    )

    assert addresses.jenkins == "https://[2001:db8::1]:18080"
    assert addresses.mysql == "[2001:db8::1]:13307"
    assert addresses.backend == "https://[2001:db8::1]:18000"
    assert addresses.frontend == "https://[2001:db8::1]:15173"


@pytest.mark.parametrize(
    "host",
    ["user@host", "host:8080", "host?query", "host#fragment", "bad..host"],
)
def test_public_host_rejects_non_host_syntax_without_echoing_value(host: str) -> None:
    config = {
        "PLATFORM_PUBLIC_HOST": host,
        "PLATFORM_PUBLIC_SCHEME": "http",
        "MYSQL_HOST_PORT": "3307",
        "JENKINS_HTTP_PORT": "8080",
        "BACKEND_HOST_PORT": "8000",
        "FRONTEND_HOST_PORT": "5173",
    }

    with pytest.raises(ConfigError) as exc_info:
        derive_public_addresses(config)

    assert "PLATFORM_PUBLIC_HOST" in str(exc_info.value)
    assert host not in str(exc_info.value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("PLATFORM_PUBLIC_SCHEME", "ftp"),
        ("JENKINS_HTTP_PORT", "0"),
        ("BACKEND_HOST_PORT", "not-a-port"),
    ],
)
def test_invalid_address_input_reports_only_key_name(key: str, value: str) -> None:
    config = {
        "PLATFORM_PUBLIC_HOST": "platform.example.test",
        "PLATFORM_PUBLIC_SCHEME": "http",
        "MYSQL_HOST_PORT": "3307",
        "JENKINS_HTTP_PORT": "8080",
        "BACKEND_HOST_PORT": "8000",
        "FRONTEND_HOST_PORT": "5173",
    }
    config[key] = value

    with pytest.raises(ConfigError) as exc_info:
        derive_public_addresses(config)

    assert key in str(exc_info.value)
    assert value not in str(exc_info.value)
