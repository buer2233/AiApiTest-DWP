# -*- coding: utf-8 -*-
"""分析 CLI 统一路径解析。

svn_analyse 位于 ``api-test-E9/E9_svn_analyse/svn_analyse/``：

- ``ANALYSE_ROOT``：E9_svn_analyse 目录，分析产物（output/）落在这里。
- ``FRAMEWORK_ROOT``：api-test-E9，接口自动化框架、skill_utils、tools 都在这里；
  不包含 E9 MCP 运行时。
- ``WORKSPACE_ROOT``：工作区根。所有代码分析通过外部 MCP 完成，不依赖本地工作副本。
"""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
ANALYSE_ROOT = PACKAGE_DIR.parent
FRAMEWORK_ROOT = ANALYSE_ROOT.parent
WORKSPACE_ROOT = FRAMEWORK_ROOT.parent

DEFAULT_OUTPUT_DIRNAME = "output"


def repo_root() -> Path:
    """返回工作区根目录。"""
    return WORKSPACE_ROOT


def output_root() -> Path:
    """返回分析产物目录 E9_svn_analyse/output/（不入 Git）。"""
    return ANALYSE_ROOT / DEFAULT_OUTPUT_DIRNAME


def ensure_framework_importable() -> None:
    """保证 api-test-E9 可导入（skill_utils、tools 等模块）。"""
    if str(FRAMEWORK_ROOT) not in sys.path:
        sys.path.insert(0, str(FRAMEWORK_ROOT))
