"""统一日志、诊断和证据脱敏。"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "authorization",
    "credential",
    "api_key",
    "private_key",
)


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


class Redactor:
    def __init__(self, *, extra_secrets: Sequence[str] = ()):
        self._secrets = tuple(
            sorted({str(item) for item in extra_secrets if len(str(item)) >= 3}, key=len, reverse=True)
        )

    @classmethod
    def from_env(
        cls,
        values: Mapping[str, str],
        *,
        extra_secrets: Sequence[str] = (),
    ) -> "Redactor":
        secrets = list(extra_secrets)
        for key, value in values.items():
            if is_sensitive_key(key) or key.upper() == "JENKINS_USERNAME":
                secrets.append(value)
        return cls(extra_secrets=secrets)

    def text(self, value: object) -> str:
        result = str(value)
        for secret in self._secrets:
            result = result.replace(secret, "***")
        result = re.sub(
            r"(?i)(authorization\s*[:=]\s*(?:basic|bearer)\s+)[^\s;,]+",
            r"\1***",
            result,
        )
        result = re.sub(r"(?i)(cookie\s*[:=]\s*)[^\s;,]+", r"\1***", result)
        result = re.sub(
            r"(?i)(password|passwd|secret|token|api_key|private_key)(\s*[:=]\s*)[^\s&,;]+",
            r"\1\2***",
            result,
        )
        result = re.sub(r"(?i)(https?://)[^/@\s]+@", r"\1***@", result)
        return result

    def url(self, value: str) -> str:
        parsed = urlsplit(self.text(value))
        hostname = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        netloc = f"***@{hostname}{port}" if parsed.username or parsed.password else parsed.netloc
        query = urlencode(
            [(key, "***" if is_sensitive_key(key) else item) for key, item in parse_qsl(parsed.query)]
        )
        return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))

    def mapping(self, value: Mapping[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if is_sensitive_key(key):
                redacted[key] = "***"
            elif isinstance(item, Mapping):
                redacted[key] = self.mapping(item)
            elif isinstance(item, (list, tuple)):
                redacted[key] = [
                    self.mapping(entry) if isinstance(entry, Mapping) else self.text(entry)
                    for entry in item
                ]
            elif isinstance(item, str):
                redacted[key] = self.text(item)
            else:
                redacted[key] = item
        return redacted
