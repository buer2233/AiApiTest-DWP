# -*- coding: utf-8 -*-
"""解析用户消息中的单个 SVN revision。"""

from __future__ import annotations

import re

class RevisionParseError(ValueError):
    """用户输入无法解析为单个正整数 revision。"""


_RANGE_RE = re.compile(r"(?i)\br?\d+\s*[:\-]\s*r?\d+")
_HEAD_RE = re.compile(r"(?i)^\s*head\s*$")

# 按具体到宽泛排序，避免漏掉「Revision r349084」这类写法。
_PATTERNS = (
    re.compile(r"(?i)\brevision\s+r?(?P<rev>\d+)\b"),
    re.compile(r"(?i)\b修订\s*[：:]?\s*r?(?P<rev>\d+)\b"),
    re.compile(r"(?i)\b分析\s+r?(?P<rev>\d+)\b"),
    re.compile(r"(?i)\b实现\s+r?(?P<rev>\d+)"),
    re.compile(r"(?i)\b复测\s+r?(?P<rev>\d+)\b"),
    re.compile(r"(?i)\bretest\s+r?(?P<rev>\d+)\b"),
    re.compile(r"(?i)\br(?P<rev>\d+)\b"),
)


def parse_revision(text: str) -> int:
    """从用户消息中解析唯一的 SVN revision 号。

    接受：``r349084``、``Revision r349084``、``修订 349084``、纯数字。
    拒绝：空串、``HEAD``、范围（``r1:r2``）、一次出现多个不同版本。
    """
    if text is None:
        raise RevisionParseError("revision 文本为空")
    raw = str(text).strip()
    if not raw:
        raise RevisionParseError("revision 文本为空")
    if _HEAD_RE.match(raw):
        raise RevisionParseError("不允许使用 HEAD，请给出具体 revision")
    if _RANGE_RE.search(raw):
        raise RevisionParseError("不允许一次分析 revision 范围")

    found: list[int] = []
    if raw.isdigit():
        found.append(int(raw))
    else:
        for pattern in _PATTERNS:
            for match in pattern.finditer(raw):
                found.append(int(match.group("rev")))

    unique = list(dict.fromkeys(found))
    if not unique:
        raise RevisionParseError(f"无法从文本解析 revision: {text!r}")
    if len(unique) > 1:
        raise RevisionParseError(f"一次只允许一个 revision，实际解析到: {unique}")
    revision = unique[0]
    if revision <= 0:
        raise RevisionParseError("revision 必须为正整数")
    return revision


def revision_mark(revision: int) -> str:
    """返回 pytest / 目录使用的 ``r<rev>`` 标记。"""
    return f"r{int(revision)}"
