"""SVN revision 提交元数据采集与功能关键词提取。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from svn_analyse import paths

paths.ensure_framework_importable()

from skill_utils.api_index_db import load_revision_meta, upsert_revision_meta  # noqa: E402


# 保留 issue 编号中的英文句点，先提取编号再处理其它标点。
_SPLIT_RE = re.compile(r"[\r\n,，;；。!！?？]+")
_ISSUE_RE = re.compile(r"\bno\.\d+\b", re.IGNORECASE)
_FUNCTION_RE = re.compile(r"(?:优化|新增|修复|调整|改造)\s*([^\s,，;；。.!！?？]+?)(?:的?功能)?$")


def extract_functional_keywords(commit_msg: str) -> str:
    """从提交说明中提取编号和功能名称，使用分号连接且允许为空。"""
    keywords: list[str] = []
    for part in _SPLIT_RE.split(commit_msg or ""):
        text = part.strip()
        if not text:
            continue
        for match in _ISSUE_RE.findall(text):
            keywords.append(match)
        functional = _FUNCTION_RE.search(text)
        if functional:
            name = functional.group(1).strip(" -：:")
            if name:
                keywords.append(name)
    return ";".join(dict.fromkeys(keywords))


def record_revision_meta(
    db_path: str | Path,
    revision: int,
    log_info: dict[str, Any],
    report_path: str | Path,
) -> None:
    """将已采集的 SVN 日志字段写入 revision_meta 表。"""
    message = str(log_info.get("message") or "")
    upsert_revision_meta(
        db_path,
        revision=revision,
        commit_msg=message,
        commit_author=str(log_info.get("author") or ""),
        commit_date=str(log_info.get("date") or ""),
        functional_keywords=extract_functional_keywords(message),
        report_path=str(report_path),
    )


__all__ = ["extract_functional_keywords", "load_revision_meta", "record_revision_meta"]
