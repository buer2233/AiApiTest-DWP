"""技能运行时配置的安全读写辅助函数。"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_utils.project_root import skill_root


LogFn = Callable[[str], None] | None


def _noop(_message: str) -> None:
    """默认日志回调不输出内容。"""


def default_skill_config_path() -> Path:
    """返回 api-test 配置模块路径（仅用于兼容旧调用）。"""
    return skill_root() / "config.py"


def update_skill_config(
    update_config: dict[str, Any],
    config_path: str | Path | None = None,
    on_warn: LogFn = None,
    on_info: LogFn = None,
) -> bool:
    """原子合并并写回技能配置，日志中不包含配置值。"""
    warn = on_warn or _noop
    info = on_info or _noop
    if not isinstance(update_config, dict):
        warn("update_config 必须是字典，已跳过技能配置更新")
        return False

    target = Path(config_path) if config_path is not None else default_skill_config_path()
    current: dict[str, Any] = {}
    if target.is_file():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warn("读取技能配置失败，将以本次提供的配置重建")
        else:
            if isinstance(payload, dict):
                current = payload
            else:
                warn("技能配置不是 JSON 对象，将以本次提供的配置重建")

    current.update(update_config)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(current, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        warn("写入技能配置失败")
        return False

    info(f"已更新技能配置字段：{', '.join(sorted(map(str, update_config)))}")
    return True
