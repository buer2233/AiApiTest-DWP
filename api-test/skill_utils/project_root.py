"""根据工具位置定位 api-test 项目根目录。"""

from __future__ import annotations

from pathlib import Path


def skill_root() -> Path:
    """兼容旧调用，返回当前 api-test 根目录。"""
    return Path(__file__).resolve().parents[1]


def resolve_project_root(skill_location: str | Path | None = None) -> Path:
    """从工具文件或目录定位 api-test 根目录，不依赖当前工作目录。"""
    location = Path(skill_location).resolve() if skill_location is not None else skill_root()
    candidates = (location, *location.parents)
    for candidate in candidates:
        if (candidate / "page_api").is_dir() and (candidate / "test_case").is_dir():
            return candidate
    raise ValueError(f"无法从工具位置定位 api-test 项目根目录：{location}")
