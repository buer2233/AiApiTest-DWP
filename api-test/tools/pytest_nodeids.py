"""
pytest node id 处理工具模块

提供 node id 标准化、缓存读取和持久化功能，
用于 CI/CD 流水线中处理失败用例的 node id。
"""

import json
from pathlib import Path
from typing import Iterable


def normalize_nodeids(raw_values: Iterable[str]) -> list[str]:
    """清洗空值和重复 node id，保持 pytest 字符串格式。"""
    normalized = []
    seen = set()
    for raw_value in raw_values:
        if raw_value is None:
            continue
        nodeid = str(raw_value).strip()
        if not nodeid or nodeid in seen:
            continue
        normalized.append(nodeid)
        seen.add(nodeid)
    return normalized


def load_lastfailed(cache_dir: Path) -> list[str]:
    """读取 pytest lastfailed 缓存，返回失败 node id 列表。"""
    cache_file = Path(cache_dir) / "v" / "cache" / "lastfailed"
    if not cache_file.exists():
        return []

    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid pytest lastfailed cache: {cache_file}") from exc

    if isinstance(payload, dict):
        return normalize_nodeids(payload.keys())
    if isinstance(payload, list):
        return normalize_nodeids(payload)
    raise ValueError(f"Unsupported pytest lastfailed cache format: {cache_file}")


def write_nodeids(nodeids: list[str], output_path: Path) -> None:
    """将 node id 列表写入 JSON 文件，供 CI、Jenkins 和后端消费。"""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(normalize_nodeids(nodeids), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
