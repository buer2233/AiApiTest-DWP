# -*- coding: utf-8 -*-

"""api-test-common 前置快速检查。"""

import json
import os
import subprocess
import sys
from datetime import datetime


for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(TOOLS_DIR)
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from skill_utils.project_root import DEFAULT_CONFIG_PATH, resolve_project_root  # noqa: E402


DATE_FIELD = "apiDataUpdateDate"
MAX_INTERVAL_DAYS = 7
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d")


def _warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def _load_config() -> dict:
    if not os.path.isfile(DEFAULT_CONFIG_PATH):
        return {}
    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"读取 config.json 失败，将刷新接口索引: {exc}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _run_scan() -> int:
    scan_script = os.path.join(TOOLS_DIR, "scan_page_api.py")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, scan_script],
        cwd=_SKILL_ROOT,
        text=True,
        encoding="utf-8",
        env=env,
        capture_output=True,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
        if not result.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    return result.returncode


def main() -> int:
    if not resolve_project_root(on_warn=_warn):
        return 1

    config_data = _load_config()
    raw = config_data.get(DATE_FIELD, "")
    update_date = _parse_date(raw)
    if not update_date:
        print(f"config.json 未配置有效 {DATE_FIELD}，将刷新接口索引。")
        return _run_scan()

    today = datetime.now().date()
    delta_days = (today - update_date).days
    if delta_days < 0:
        print(f"config.json 中填写的 {DATE_FIELD} 时间有误，将刷新接口索引：{raw!r}")
        return _run_scan()
    if delta_days <= MAX_INTERVAL_DAYS:
        print("接口索引为一周内的最新数据，无需更新。")
        return 0

    code = _run_scan()
    if code != 0:
        print("接口索引更新失败，请根据上方日志处理。", file=sys.stderr)
        return code
    print("本次扫描出的新增接口信息见上方 [scan_page_api] recent_new_methods 输出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
