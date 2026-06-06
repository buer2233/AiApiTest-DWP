# -*- coding: utf-8 -*-

"""Claude Code PreToolUse hook：触发 api-test-common 时执行前置检查。"""

import json
import os
import subprocess
import sys


HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HOOK_DIR)
PREFLIGHT_SCRIPT = os.path.join(SKILL_ROOT, "tools", "preflight_check.py")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    skill_name = (tool_input.get("skill") or "").strip()
    if skill_name != "api-test-common":
        return 0

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [sys.executable, PREFLIGHT_SCRIPT],
            cwd=payload.get("cwd") or os.getcwd(),
            text=True,
            encoding="utf-8",
            env=env,
            capture_output=True,
            timeout=120,
        )
    except Exception as exc:
        err_ctx = f"[preflight_hook] 执行 preflight_check.py 失败: {exc}"
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": err_ctx,
            }
        }, ensure_ascii=False))
        return 0

    output_blob = (result.stdout or "") + (result.stderr or "")
    context_text = (
        "[preflight_check] 入口前置检查结果（由 hook 自动执行）：\n"
        + output_blob.strip()
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context_text,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
