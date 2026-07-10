"""运行日志与错误摘要的基础敏感信息脱敏。"""

from __future__ import annotations

import re


REDACTED = "[REDACTED]"
SENSITIVE_KEY = r"(?:authorization|proxy-authorization|cookie|set-cookie|password|passwd|secret|token|api[_-]?key)"
SENSITIVE_KEY_PREFIX = rf"((?:\\?[\"'])?{SENSITIVE_KEY}(?:\\?[\"'])?\s*[:=]\s*)"


def redact_sensitive_text(value: str | None) -> str:
    text = str(value or "")
    text = re.sub(
        r"(?i)(\b(?:authorization|proxy-authorization)\s*:\s*)(?:basic|bearer)?\s*[^\s,;]+",
        rf"\1{REDACTED}",
        text,
    )
    text = re.sub(r"(?i)(\b(?:cookie|set-cookie)\s*:\s*)[^\r\n]+", rf"\1{REDACTED}", text)

    # 先处理完整引号值，避免仅遮蔽第一个空格前的片段。转义引号用于日志中的 JSON/repr 文本。
    for delimiter in (r'\"', r"\'", '"', "'"):
        escaped_delimiter = re.escape(delimiter)
        text = re.sub(
            rf"(?is){SENSITIVE_KEY_PREFIX}({escaped_delimiter})(?:\\.|(?!{escaped_delimiter}).)*?({escaped_delimiter})",
            lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}{match.group(3)}",
            text,
        )
    text = re.sub(
        rf"(?i){SENSITIVE_KEY_PREFIX}(?!\\?[\"'])[^\s,;}}]+",
        rf"\1{REDACTED}",
        text,
    )
    return text
