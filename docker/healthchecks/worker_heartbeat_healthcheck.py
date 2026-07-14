"""检查 Jenkins 同步 worker 心跳文件是否仍在新鲜阈值内。"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


DEFAULT_HEARTBEAT_PATH = "/tmp/aiapitest-dwp/jenkins-sync-worker.heartbeat"
DEFAULT_MAX_AGE_SECONDS = 60


def is_heartbeat_fresh(
    heartbeat_path: Path,
    *,
    max_age_seconds: int,
    now: float | None = None,
) -> bool:
    """只依据文件修改时间判断心跳，避免解析或暴露业务内容。"""
    try:
        modified_at = heartbeat_path.stat().st_mtime
    except OSError:
        return False

    current_time = time.time() if now is None else now
    return max(0.0, current_time - modified_at) <= max_age_seconds


def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def main() -> int:
    heartbeat_path = Path(os.getenv("JENKINS_SYNC_HEARTBEAT_PATH", DEFAULT_HEARTBEAT_PATH))
    max_age_seconds = _positive_int_from_env(
        "JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS",
        DEFAULT_MAX_AGE_SECONDS,
    )
    if is_heartbeat_fresh(heartbeat_path, max_age_seconds=max_age_seconds):
        return 0
    print("worker heartbeat is missing or stale", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
