import json
import sqlite3
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / ".claude" / "skills" / "api-test-common"


def test_project_root_resolves_ai_api_test_project():
    sys.path.insert(0, str(SKILL_ROOT))
    try:
        from skill_utils.project_root import get_temp_dir, resolve_project_root

        assert Path(resolve_project_root()) == PROJECT_ROOT
        assert Path(get_temp_dir()) == PROJECT_ROOT / "runtime"
    finally:
        sys.path.remove(str(SKILL_ROOT))


def test_scan_page_api_builds_index(tmp_path):
    db_path = tmp_path / "page_api_index.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "tools" / "scan_page_api.py"),
            "--db",
            str(db_path),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()
    assert "methods=" in result.stdout
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT api_url, api_name FROM api_methods").fetchall()
    assert rows
    assert ("/", "demo_get") in rows


def test_match_captures_creates_selection_from_jsonl(tmp_path):
    jsonl_path = tmp_path / "latest.jsonl"
    out_path = tmp_path / "capture_selection.md"
    jsonl_path.write_text(
        json.dumps(
            {
                "method": "GET",
                "pure_path": "/api/demo",
                "url": "https://movie.douban.com/api/demo",
                "status": 200,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "tools" / "match_captures.py"),
            "--jsonl",
            str(jsonl_path),
            "--out",
            str(out_path),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "GET `/api/demo`" in out_path.read_text(encoding="utf-8")


def test_match_captures_no_longer_auto_ignores_login_paths(tmp_path):
    jsonl_path = tmp_path / "latest.jsonl"
    out_path = tmp_path / "capture_selection.md"
    jsonl_path.write_text(
        json.dumps(
            {
                "method": "POST",
                "pure_path": "/login",
                "url": "https://movie.douban.com/login",
                "status": 200,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "tools" / "match_captures.py"),
            "--jsonl",
            str(jsonl_path),
            "--out",
            str(out_path),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    content = out_path.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert "POST `/login`" in content
    assert "已自动忽略的登录/登出接口" not in content
