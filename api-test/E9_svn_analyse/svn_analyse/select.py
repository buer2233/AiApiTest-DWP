"""按功能关键词或 SVN revision 选取关联接口自动化用例。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from svn_analyse import paths

paths.ensure_framework_importable()

from skill_utils.api_index_db import connect, ensure_schema  # noqa: E402


def select_by_keyword(db_path: str | Path, keyword: str) -> list[dict[str, object]]:
    """查询提交说明命中关键词且存在同 revision mark 的测试方法。"""
    text = keyword.strip()
    if not text:
        raise ValueError("keyword 不能为空")
    with connect(db_path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT rm.revision, rm.commit_msg, tm.test_name, tm.file, tm.title, tm.marks, tm.line
            FROM revision_meta rm
            JOIN test_methods tm
              ON instr(';' || tm.marks || ';', ';r' || rm.revision || ';') > 0
            WHERE rm.commit_msg LIKE ? OR rm.functional_keywords LIKE ?
            ORDER BY rm.revision, tm.file, tm.line
            """,
            (f"%{text}%", f"%{text}%"),
        ).fetchall()
    return [dict(row) for row in rows]


def select_by_revision(db_path: str | Path, revision: int) -> list[dict[str, object]]:
    """查询带指定 `r<revision>` mark 的全部测试方法。"""
    if revision <= 0:
        raise ValueError("revision 必须为正整数")
    with connect(db_path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT tm.test_name, tm.file, tm.title, tm.marks, tm.calls, tm.line,
                   rm.commit_msg
            FROM test_methods tm
            LEFT JOIN revision_meta rm ON rm.revision = ?
            WHERE instr(';' || tm.marks || ';', ';r' || ? || ';') > 0
            ORDER BY tm.file, tm.line
            """,
            (revision, revision),
        ).fetchall()
    return [dict(row) for row in rows]
