"""page_api 覆盖索引的 SQLite 读写工具。"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_FILENAME = "page_api_index.sqlite3"

_METHOD_COLUMNS = (
    "api_url",
    "http_method",
    "api_name",
    "api_desc",
    "class_name",
    "class_bases",
    "file",
    "line",
    "author",
    "create_date",
    "is_ai",
    "mtime",
)

_INSERT_METHOD_SQL = f"""
INSERT INTO api_methods ({", ".join(_METHOD_COLUMNS)})
VALUES ({", ".join("?" for _ in _METHOD_COLUMNS)})
ON CONFLICT(api_url, http_method) DO UPDATE SET
    api_name = excluded.api_name,
    api_desc = excluded.api_desc,
    class_name = excluded.class_name,
    class_bases = excluded.class_bases,
    file = excluded.file,
    line = excluded.line,
    author = excluded.author,
    create_date = excluded.create_date,
    is_ai = excluded.is_ai,
    mtime = excluded.mtime
"""

_INSERT_NEW_METHOD_SQL = f"""
INSERT OR IGNORE INTO api_methods ({", ".join(_METHOD_COLUMNS)})
VALUES ({", ".join("?" for _ in _METHOD_COLUMNS)})
"""


def get_default_db_path(tools_dir: str | Path) -> Path:
    """返回运行时目录中的默认索引数据库路径，避免提交生成物。"""
    tools_path = Path(tools_dir)
    return tools_path.parent / "runtime" / DB_FILENAME


def connect(db_path: str | Path) -> sqlite3.Connection:
    """创建带字段名访问能力的 SQLite 连接。"""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    """确保 E9 URL 索引表和索引元数据表存在。"""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_url TEXT NOT NULL,
            http_method TEXT NOT NULL DEFAULT '',
            api_name TEXT NOT NULL DEFAULT '',
            api_desc TEXT NOT NULL DEFAULT '',
            class_name TEXT NOT NULL DEFAULT '',
            class_bases TEXT NOT NULL DEFAULT '[]',
            file TEXT NOT NULL DEFAULT '',
            line INTEGER NOT NULL DEFAULT 0,
            author TEXT NOT NULL DEFAULT '',
            create_date TEXT NOT NULL DEFAULT '',
            is_ai TEXT NOT NULL DEFAULT '',
            mtime INTEGER NOT NULL DEFAULT 0,
            UNIQUE(api_url, http_method)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS revision_meta (
            revision INTEGER PRIMARY KEY,
            commit_msg TEXT NOT NULL DEFAULT '',
            commit_author TEXT NOT NULL DEFAULT '',
            commit_date TEXT NOT NULL DEFAULT '',
            functional_keywords TEXT NOT NULL DEFAULT '',
            analyzed_at TEXT NOT NULL DEFAULT '',
            report_path TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS test_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name TEXT NOT NULL,
            file TEXT NOT NULL,
            marks TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            calls TEXT NOT NULL DEFAULT '',
            line INTEGER NOT NULL DEFAULT 0,
            UNIQUE(file, line, test_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS index_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_api_methods_url ON api_methods(api_url)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_api_methods_url_method "
        "ON api_methods(api_url, http_method)"
    )
    connection.commit()


def _record_to_row(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """将扫描记录规范化为 api_methods 的插入列顺序。"""
    bases = record.get("class_bases", record.get("bases", []))
    if not isinstance(bases, str):
        bases = json.dumps(bases if bases is not None else [], ensure_ascii=False)
    return (
        str(record.get("api_url") or record.get("pure_path") or "").strip(),
        str(record.get("http_method") or record.get("method") or "").strip().upper(),
        str(record.get("api_name") or record.get("name") or ""),
        str(record.get("api_desc") or record.get("description") or ""),
        str(record.get("class_name") or record.get("class") or ""),
        bases,
        str(record.get("file") or ""),
        int(record.get("line") or 0),
        str(record.get("author") or record.get("Author") or ""),
        str(record.get("create_date") or record.get("Create Date") or ""),
        str(record.get("is_ai") or record.get("IsAI") or ""),
        int(record.get("mtime") or 0),
    )


def _write_metadata(
    connection: sqlite3.Connection, metadata: Mapping[str, Any] | None
) -> None:
    """在提供元数据时以本次扫描结果完整替换元数据表。"""
    if metadata is None:
        return
    connection.execute("DELETE FROM index_metadata")
    connection.executemany(
        "INSERT INTO index_metadata(key, value) VALUES (?, ?)",
        [(str(key), str(value)) for key, value in metadata.items()],
    )


def replace_index(
    db_path: str | Path,
    records: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """用本次扫描记录事务性替换索引，并写入可选元数据。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute("DELETE FROM api_methods")
        connection.executemany(_INSERT_METHOD_SQL, [_record_to_row(record) for record in records])
        _write_metadata(connection, metadata)
        connection.commit()


def insert_methods(
    db_path: str | Path,
    records: Iterable[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> int:
    """仅插入尚未存在的 URL/HTTP 方法组合并返回实际新增数量。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [_record_to_row(record) for record in records]
    with connect(path) as connection:
        ensure_schema(connection)
        inserted = 0
        for row in rows:
            cursor = connection.execute(_INSERT_NEW_METHOD_SQL, row)
            inserted += cursor.rowcount
        _write_metadata(connection, metadata)
        connection.commit()
    return inserted


def is_empty(db_path: str | Path) -> bool:
    """数据库不存在或接口索引没有记录时返回 True。"""
    path = Path(db_path)
    if not path.is_file():
        return True
    with connect(path) as connection:
        ensure_schema(connection)
        return connection.execute("SELECT 1 FROM api_methods LIMIT 1").fetchone() is None


def existing_url_method_pairs(db_path: str | Path) -> set[tuple[str, str]]:
    """读取已入库的规范化 URL/HTTP 方法组合，供增量扫描差分使用。"""
    path = Path(db_path)
    if not path.is_file():
        return set()
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute("SELECT api_url, http_method FROM api_methods").fetchall()
    return {
        ((row["api_url"] or "").strip(), (row["http_method"] or "").strip().upper())
        for row in rows
    }


def load_metadata(db_path: str | Path) -> dict[str, str]:
    """读取索引元数据；数据库不存在时返回空字典。"""
    path = Path(db_path)
    if not path.is_file():
        return {}
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute("SELECT key, value FROM index_metadata ORDER BY key").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def load_methods(db_path: str | Path) -> list[dict[str, object]]:
    """读取全部接口索引记录，供脱敏库存快照和覆盖查询使用。"""
    path = Path(db_path)
    if not path.is_file():
        return []
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            f"SELECT {', '.join(_METHOD_COLUMNS)} FROM api_methods "
            "ORDER BY file, line, api_name, api_url, http_method"
        ).fetchall()
    methods: list[dict[str, object]] = []
    for row in rows:
        try:
            bases = json.loads(row["class_bases"] or "[]")
        except json.JSONDecodeError:
            bases = []
        methods.append(
            {
                "api_url": row["api_url"],
                "http_method": row["http_method"],
                "api_name": row["api_name"],
                "api_desc": row["api_desc"],
                "class_name": row["class_name"],
                "class_bases": bases,
                "file": row["file"],
                "line": row["line"],
                "author": row["author"],
                "create_date": row["create_date"],
                "is_ai": row["is_ai"],
                "mtime": row["mtime"],
            }
        )
    return methods


def find_methods_by_endpoint(
    db_path: str | Path, api_url: str, http_method: str
) -> list[dict[str, object]]:
    """按 URL 和 HTTP 方法等值查询已有封装，空方法记录可作为兜底。"""
    path = Path(db_path)
    if not path.is_file():
        return []
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT api_name, class_name, file, line, http_method
            FROM api_methods
            WHERE api_url = ? AND (http_method = ? OR http_method = '')
            ORDER BY CASE WHEN http_method = ? THEN 0 ELSE 1 END, id
            """,
            (api_url, http_method.strip().upper(), http_method.strip().upper()),
        ).fetchall()
    return [
        {
            "api_name": row["api_name"],
            "class_name": row["class_name"],
            "file": row["file"],
            "line": row["line"],
            "http_method": row["http_method"],
        }
        for row in rows
    ]


def upsert_revision_meta(
    db_path: str | Path,
    *,
    revision: int,
    commit_msg: str,
    commit_author: str,
    commit_date: str,
    functional_keywords: str,
    report_path: str,
) -> None:
    """写入或更新单个 SVN revision 的元数据。"""
    if revision <= 0:
        raise ValueError("revision 必须为正整数")
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    analyzed_at = datetime.now(timezone.utc).isoformat()
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO revision_meta(
                revision, commit_msg, commit_author, commit_date,
                functional_keywords, analyzed_at, report_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(revision) DO UPDATE SET
                commit_msg = excluded.commit_msg,
                commit_author = excluded.commit_author,
                commit_date = excluded.commit_date,
                functional_keywords = excluded.functional_keywords,
                analyzed_at = excluded.analyzed_at,
                report_path = excluded.report_path
            """,
            (
                revision,
                commit_msg,
                commit_author,
                commit_date,
                functional_keywords,
                analyzed_at,
                report_path,
            ),
        )
        connection.commit()


def load_revision_meta(db_path: str | Path, revision: int) -> dict[str, object] | None:
    """读取指定 revision 的元数据；不存在时返回 None。"""
    path = Path(db_path)
    if not path.is_file():
        return None
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            """
            SELECT revision, commit_msg, commit_author, commit_date,
                   functional_keywords, analyzed_at, report_path
            FROM revision_meta WHERE revision = ?
            """,
            (revision,),
        ).fetchone()
    return dict(row) if row is not None else None


def replace_test_methods(db_path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    """用当前 test_case 扫描结果替换 test_methods 表。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        (
            str(record.get("test_name") or ""),
            str(record.get("file") or ""),
            str(record.get("marks") or ""),
            str(record.get("title") or ""),
            str(record.get("calls") or ""),
            int(record.get("line") or 0),
        )
        for record in records
    ]
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute("DELETE FROM test_methods")
        connection.executemany(
            """
            INSERT INTO test_methods(test_name, file, marks, title, calls, line)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()


def load_test_methods(db_path: str | Path) -> list[dict[str, object]]:
    """读取 test_methods 表的脱敏记录。"""
    path = Path(db_path)
    if not path.is_file():
        return []
    with connect(path) as connection:
        ensure_schema(connection)
        rows = connection.execute(
            "SELECT test_name, file, marks, title, calls, line "
            "FROM test_methods ORDER BY file, line, test_name"
        ).fetchall()
    return [dict(row) for row in rows]
