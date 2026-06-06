# -*- coding: utf-8 -*-

"""项目根定位与运行时产物目录解析。

本 skill 是可随 ai-api-test 框架复制到任意项目的项目内 skill，默认位置为
`<project>/.claude/skills/api-test-common/`。项目根由 skill 自身位置向上三层
推导，校验目标项目必须包含 `config.py` 和 `test_case/`。
"""

import os
from typing import Callable, Optional


TEMP_DIR_NAME = "runtime"
CONFIG_FILENAME = "config.json"

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(SKILL_ROOT, CONFIG_FILENAME)
PROJECT_ROOT = os.path.normpath(os.path.join(SKILL_ROOT, "..", "..", ".."))


LogFn = Optional[Callable[[str], None]]


def _noop(_msg: str) -> None:
    pass


def resolve_project_root(
    on_warn: LogFn = None,
    on_info: LogFn = None,
) -> Optional[str]:
    """返回项目根绝对路径。"""
    warn = on_warn or _noop
    info = on_info or _noop
    required = ["config.py", "test_case"]
    missing = [name for name in required if not os.path.exists(os.path.join(PROJECT_ROOT, name))]
    if missing:
        warn(
            f"未在推导出的项目根下找到必要文件/目录 {missing}: {PROJECT_ROOT}。"
            "请确认 skill 安装在 <project>/.claude/skills/api-test-common/ 路径下。"
        )
        return None
    info(f"使用项目根 {PROJECT_ROOT}")
    return PROJECT_ROOT


def get_temp_dir(
    on_warn: LogFn = None,
    on_info: LogFn = None,
) -> Optional[str]:
    """返回 `<project>/runtime` 目录绝对路径，并确保其存在。"""
    repo_root = resolve_project_root(on_warn=on_warn, on_info=on_info)
    if not repo_root:
        return None
    temp_dir = os.path.join(repo_root, TEMP_DIR_NAME)
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
