# -*- coding: utf-8 -*-
"""四期 T4.3：前置测试数据生命周期运行器。

统一调度各模块的 ``prepare_<module>_test_data.py`` 工具，承担：

- ``status``：查看模块状态文件与数据计划是否就绪；
- ``build``：幂等构建（工具自身依据状态文件复用已有对象），
  构建后补齐受管字段并通过敏感信息扫描门禁；
- ``cleanup``：按状态文件回收可再生产物（清理仅作用于状态文件登记的
  对象，失败不抛出全流程 INTERNALERROR，退出码交由调用方决策）。

数据计划 schema（``<module>_data_plan.json``）：

```json
{
  "schema_version": "t4.3-v1",
  "module": "board",
  "revision": 349149,
  "prepare_tool": "tools/prepare_board_test_data.py",
  "state_file": "test_data/board/board_test_data.json",
  "steps": [
    {"id": "query_dm", "kind": "query", "description": "...",
     "endpoint": "POST /api/...", "depends_on": [], "object_key": ""}
  ],
  "cleanup": {"policy": "state_file_only", "flag": "--cleanup"},
  "owner": "tools/prepare_board_test_data.py",
  "tag": "r349149"
}
```

状态文件只允许业务 ID、字段名与探测值；出现凭据类键名即构建门禁失败。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.sensitive_data import SENSITIVE_KEY  # noqa: E402

PLAN_SCHEMA_VERSION = "t4.3-v1"
VALID_STEP_KINDS = ("query", "create", "configure", "verify")
CLEANUP_POLICY_STATE_ONLY = "state_file_only"

# 模块注册表：工具、状态文件、数据计划与关键对象键。
# 新增模块时在此登记，即可被 status/build/cleanup 统一调度。
MODULE_REGISTRY: dict[str, dict[str, object]] = {
    "board": {
        "tool": "tools/prepare_board_test_data.py",
        "state": "test_data/board/board_test_data.json",
        "plan": "test_data/board/board_data_plan.json",
        "revision": 349149,
        "objects": ["board_id", "widget_id", "filter_widget_id"],
    },
    "doc_func": {
        "tool": "tools/prepare_doc_func_test_data.py",
        "state": "test_data/doc_func/doc_func_test_data.json",
        "plan": "test_data/doc_func/doc_func_data_plan.json",
        "revision": 349155,
        "objects": ["doc_id", "imagefile_id", "sec_category_id"],
    },
    "formmode": {
        "tool": "tools/prepare_formmode_test_data.py",
        "state": "test_data/formmode/formmode_test_data.json",
        "plan": "test_data/formmode/formmode_data_plan.json",
        "revision": 349152,
        "objects": ["mode_id", "form_id", "billid"],
    },
}

_SENSITIVE_KEY = re.compile(SENSITIVE_KEY, re.I)
_MANAGED_KEYS = ("_schema_version", "_module", "_owner", "_tag")


class RunnerError(RuntimeError):
    """运行器可预期失败：模块未登记、状态缺失、门禁未过等。"""


def get_module_spec(module: str, registry: dict[str, dict[str, object]] | None = None) -> dict[str, object]:
    table = registry if registry is not None else MODULE_REGISTRY
    if module not in table:
        known = ", ".join(sorted(table))
        raise RunnerError(f"模块 {module} 未登记；已登记模块：{known}")
    return table[module]


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_data_plan(plan: dict) -> list[str]:
    """校验数据计划 schema，返回问题列表（空列表表示通过）。"""
    problems: list[str] = []
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        problems.append(f"schema_version 必须为 {PLAN_SCHEMA_VERSION}")
    for field in ("module", "prepare_tool", "state_file", "owner", "tag"):
        if not plan.get(field):
            problems.append(f"缺少必填字段 {field}")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append("steps 不能为空，至少包含 query/create/configure/verify 之一")
        return problems
    ids: set[str] = set()
    for index, step in enumerate(steps):
        step_id = step.get("id") or f"step{index}"
        if not step.get("id"):
            problems.append(f"第 {index} 步缺少 id")
        kind = step.get("kind")
        if kind not in VALID_STEP_KINDS:
            problems.append(f"{step_id}: kind 必须取自 {VALID_STEP_KINDS}")
        if not step.get("description"):
            problems.append(f"{step_id}: 缺少 description")
        if kind == "create" and not step.get("object_key"):
            problems.append(f"{step_id}: create 步骤必须给出 object_key")
        for dep in step.get("depends_on") or []:
            if dep not in {item.get("id") for item in steps}:
                problems.append(f"{step_id}: depends_on 引用了不存在的步骤 {dep}")
        if step_id in ids:
            problems.append(f"步骤 id 重复：{step_id}")
        ids.add(step_id)
    cleanup = plan.get("cleanup") or {}
    if cleanup.get("policy") != CLEANUP_POLICY_STATE_ONLY:
        problems.append(f"cleanup.policy 必须为 {CLEANUP_POLICY_STATE_ONLY}（只回收状态文件登记对象）")
    return problems


def scan_state_sensitive(state: dict) -> list[str]:
    """状态文件敏感信息门禁：凭据类键名一律禁止。"""
    hits: list[str] = []
    for key in state:
        if _SENSITIVE_KEY.search(str(key)):
            hits.append(str(key))
    return hits


def ensure_managed_fields(state_path: Path, module: str, spec: dict) -> dict:
    """构建成功后补齐受管字段（版本/模块/owner/tag），保留业务键不变。"""
    state = load_json(state_path)
    state.setdefault("_schema_version", PLAN_SCHEMA_VERSION)
    state.setdefault("_module", module)
    state.setdefault("_owner", str(spec.get("tool") or ""))
    state.setdefault("_tag", f"r{spec.get('revision')}")
    save_json(state_path, state)
    return state


def run_tool(spec: dict[str, object], extra_args: list[str], cwd: Path | None = None) -> int:
    """以子进程方式执行准备工具，保持其自身的参数契约。"""
    tool_path = PROJECT_ROOT / str(spec.get("tool"))
    if not tool_path.is_file():
        raise RunnerError(f"准备工具不存在：{tool_path}")
    completed = subprocess.run(
        [sys.executable, str(tool_path), *extra_args],
        cwd=str(cwd or PROJECT_ROOT),
        check=False,
    )
    return int(completed.returncode)


def command_status(module: str, registry=None) -> int:
    spec = get_module_spec(module, registry)
    state_path = PROJECT_ROOT / str(spec["state"])
    plan_path = PROJECT_ROOT / str(spec["plan"])
    state = load_json(state_path)
    plan = load_json(plan_path)
    objects = {key: state.get(key) for key in spec.get("objects", [])}  # type: ignore[union-attr]  # 对象键取自注册表，类型已约束
    missing = [key for key, value in objects.items() if value in (None, "")]
    plan_problems = validate_data_plan(plan) if plan else ["数据计划文件缺失"]
    payload = {
        "module": module,
        "state_file": str(spec["state"]),
        "state_exists": state_path.is_file(),
        "objects": objects,
        "missing_objects": missing,
        "managed_fields_present": all(key in state for key in _MANAGED_KEYS),
        "plan_valid": not plan_problems,
        "plan_problems": plan_problems,
        "ready": state_path.is_file() and not missing and not plan_problems,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ready"] else 1


def command_build(module: str, extra_args: list[str], registry=None) -> int:
    spec = get_module_spec(module, registry)
    state_path = PROJECT_ROOT / str(spec["state"])
    plan_path = PROJECT_ROOT / str(spec["plan"])
    plan = load_json(plan_path)
    plan_problems = validate_data_plan(plan) if plan else ["数据计划文件缺失"]
    if plan_problems:
        raise RunnerError("数据计划未通过校验：" + "；".join(plan_problems))
    code = run_tool(spec, extra_args)
    if code != 0:
        return code
    if not state_path.is_file():
        raise RunnerError(f"构建结束但状态文件缺失：{state_path}")
    state = ensure_managed_fields(state_path, module, spec)
    hits = scan_state_sensitive(state)
    if hits:
        raise RunnerError(f"状态文件含敏感键名 {hits}，禁止入库；请清理后重建")
    print(
        json.dumps(
            {"module": module, "build": "ok", "state_file": str(spec["state"])},
            ensure_ascii=False,
        )
    )
    return 0


def command_cleanup(module: str, registry=None) -> int:
    spec = get_module_spec(module, registry)
    cleanup_flag = str((load_json(PROJECT_ROOT / str(spec["plan"])).get("cleanup") or {}).get("flag") or "--cleanup")
    code = run_tool(spec, [cleanup_flag])
    if code != 0:
        # 清理失败不阻断业务测试：如实汇报退出码，由调用方决策
        print(f"模块 {module} 清理退出码 {code}；请按状态文件人工核对残留对象", file=sys.stderr)
        return code
    print(json.dumps({"module": module, "cleanup": "ok"}, ensure_ascii=False))
    return 0


def command_list(registry=None) -> int:
    table = registry if registry is not None else MODULE_REGISTRY
    rows = []
    for name, spec in sorted(table.items()):
        state_path = PROJECT_ROOT / str(spec["state"])
        state = load_json(state_path)
        rows.append(
            {
                "module": name,
                "revision": spec.get("revision"),
                "state_exists": state_path.is_file(),
                "objects_present": [key for key in spec.get("objects", []) if state.get(key)],  # type: ignore[union-attr]  # 对象键取自注册表，类型已约束
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E9 前置测试数据生命周期运行器（四期 T4.3）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    status = sub.add_parser("status", help="查看模块状态文件与数据计划就绪情况")
    status.add_argument("--module", required=True)
    build = sub.add_parser("build", help="幂等构建前置数据（构建后过敏感信息门禁）")
    build.add_argument("--module", required=True)
    build.add_argument("--tool-arg", action="append", default=[], help="透传给准备工具的参数，可重复")
    cleanup = sub.add_parser("cleanup", help="按状态文件回收构建对象")
    cleanup.add_argument("--module", required=True)
    sub.add_parser("list", help="列出已登记模块与状态概要")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "status":
            return command_status(args.module)
        if args.cmd == "build":
            return command_build(args.module, list(args.tool_arg))
        if args.cmd == "cleanup":
            return command_cleanup(args.module)
        if args.cmd == "list":
            return command_list()
    except RunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
