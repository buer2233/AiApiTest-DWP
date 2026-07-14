"""根私有配置的受限解析与安全边界。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ConfigError(ValueError):
    """配置缺失或格式非法；异常消息只包含键名。"""


def parse_bounded_int(
    raw: object,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.strip()


def _parse_value(raw: str) -> str:
    value = _strip_inline_comment(raw.strip())
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConfigError("invalid quoted value") from exc
    return value


@dataclass(frozen=True)
class DotEnvConfig:
    values: dict[str, str]
    warnings: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path) -> "DotEnvConfig":
        if not path.is_file():
            raise ConfigError(f"configuration file missing: {path.name}")
        values: dict[str, str] = {}
        warnings: list[str] = []
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(
                f"configuration file unreadable: {path.name}; category={type(exc).__name__}"
            ) from None
        except UnicodeError as exc:
            raise ConfigError(
                f"configuration file encoding invalid: {path.name}; category={type(exc).__name__}"
            ) from None
        for line_number, raw_line in enumerate(content.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                raise ConfigError(f"invalid configuration line: {line_number}")
            key, raw_value = line.split("=", 1)
            key = key.strip()
            if not key or not key.replace("_", "A").isalnum() or not (key[0].isalpha() or key[0] == "_"):
                raise ConfigError(f"invalid configuration key at line: {line_number}")
            if key in values:
                warnings.append(f"duplicate key: {key}")
            values[key] = _parse_value(raw_value)
        return cls(values=values, warnings=tuple(warnings))

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.values.get(name, default)

    def key_status(self, names: Iterable[str]) -> dict[str, str]:
        return {
            name: "present" if name in self.values and self.values[name] != "" else "missing"
            for name in names
        }

    def require(self, names: Iterable[str]) -> dict[str, str]:
        requested = tuple(names)
        missing = [name for name in requested if not self.values.get(name)]
        if missing:
            raise ConfigError("required configuration keys missing: " + ", ".join(missing))
        return {name: self.values[name] for name in requested}
