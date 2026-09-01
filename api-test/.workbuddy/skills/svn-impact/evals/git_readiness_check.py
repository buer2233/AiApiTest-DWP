"""提交前只读审计生成产物与本地索引。

按三期变更（撤回「不提交真实凭据」红线），测试环境凭据文件
（config.json、test_data/account.json）允许提交团队内部 GitLab，
不再列入阻断清单；运行时产物与本地索引仍禁止提交。
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable


BLOCKED_DIRECTORIES = (
    "report",
    "runtime",
    "logs",
    # .codegraph 目录已删除，不再需要排除
    ".workbuddy/memory",
)
BLOCKED_FILES = (
    "page_api_index.sqlite3",
)


def _normalized_allowlist(allowlist: Iterable[str]) -> set[str]:
    return {Path(item).as_posix().rstrip("/") for item in allowlist}


def _is_allowed(relative_path: str, allowlist: set[str]) -> bool:
    normalized = relative_path.rstrip("/")
    return normalized in allowlist


def _run_git(repo_root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None


def _is_tracked_or_staged(repo_root: Path, relative_path: str) -> bool:
    candidate = relative_path.rstrip("/")
    completed = _run_git(repo_root, ["ls-files", "--", candidate])
    return bool(completed and completed.returncode == 0 and completed.stdout.strip())


def _is_ignored(repo_root: Path, relative_path: str) -> bool:
    candidate = relative_path.rstrip("/")
    completed = _run_git(repo_root, ["check-ignore", "-q", "--", candidate])
    return bool(completed and completed.returncode == 0)


def _would_be_committed(repo_root: Path, relative_path: str) -> bool:
    """仅当 Git 已跟踪或暂存时，才把本地产物视为提交候选。"""
    return _is_tracked_or_staged(repo_root, relative_path) or not _is_ignored(
        repo_root, relative_path
    )


def find_commit_blockers(repo_root: Path, allowlist: Iterable[str] = ()) -> list[str]:
    """返回阻断提交的相对路径，且绝不读取文件内容。"""
    root = repo_root.resolve()
    allowed = _normalized_allowlist(allowlist)
    blockers: set[str] = set()

    for relative in BLOCKED_DIRECTORIES:
        candidate = root / relative
        display = f"{Path(relative).as_posix().rstrip('/')}/"
        if (
            candidate.exists()
            and not _is_allowed(display, allowed)
            and _would_be_committed(root, display)
        ):
            blockers.add(display)

    for relative in BLOCKED_FILES:
        candidate = root / relative
        display = Path(relative).as_posix()
        if (
            candidate.is_file()
            and not _is_allowed(display, allowed)
            and _would_be_committed(root, display)
        ):
            blockers.add(display)

    for directory in root.rglob("__pycache__"):
        if directory.is_dir() and ".git" not in directory.parts:
            display = f"{directory.relative_to(root).as_posix().rstrip('/')}/"
            if not _is_allowed(display, allowed) and _would_be_committed(root, display):
                blockers.add(display)

    return sorted(blockers)


def main() -> int:
    parser = argparse.ArgumentParser(description="在提交前检查仓库。")
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="相对路径",
        help="显式放行一个已知相对路径；可重复指定。",
    )
    args = parser.parse_args()
    blockers = find_commit_blockers(args.repo_root, args.allow)
    if blockers:
        print("敏感或生成路径阻断提交：")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("Git 提交准备检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
