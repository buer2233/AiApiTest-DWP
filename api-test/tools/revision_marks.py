# -*- coding: utf-8 -*-
"""扫描并注册 SVN revision pytest mark（r<digits>）。"""

from __future__ import annotations

import re
from pathlib import Path

REVISION_MARK_RE = re.compile(r"pytest\.mark\.(r\d+)")


def collect_revision_marks(test_root: str | Path) -> list[str]:
    """从用例源码中收集 ``@pytest.mark.r123`` 形式的标记。"""
    root = Path(test_root)
    marks: set[str] = set()
    if not root.is_dir():
        return []
    for py_file in root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        marks.update(REVISION_MARK_RE.findall(text))
    return sorted(marks)


def register_revision_marks(config, test_root: str | Path) -> list[str]:
    """向 pytest config 注册已出现的 r<rev> mark，避免 UnknownMarkWarning。"""
    config.addinivalue_line(
        "markers",
        "svn_revision: targeted regression for an SVN revision; also use r<digits> e.g. r349084",
    )
    marks = collect_revision_marks(test_root)
    for mark in marks:
        config.addinivalue_line(
            "markers",
            f"{mark}: SVN revision {mark} targeted regression",
        )
    return marks
