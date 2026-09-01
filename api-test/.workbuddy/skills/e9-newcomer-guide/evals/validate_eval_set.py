"""校验 E9 新人引导技能的触发集和工作流评估集。"""

from __future__ import annotations

import json
from pathlib import Path


def validate_eval_sets(eval_dir: Path) -> list[str]:
    errors: list[str] = []
    payloads = {}
    for name in ("trigger_eval_set.json", "workflow_eval_set.json"):
        path = eval_dir / name
        try:
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # 评估资产损坏时给出可读错误
            errors.append(f"{name} 无法读取：{exc}")
    for name, payload in payloads.items():
        if payload.get("schema_version") != 1 or payload.get("skill_name") != "e9-newcomer-guide":
            errors.append(f"{name} 的 schema_version 或 skill_name 不正确")
        cases = payload.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append(f"{name} 的 cases 必须是非空数组")
            continue
        ids = [case.get("id") for case in cases if isinstance(case, dict)]
        if len(ids) != len(set(ids)):
            errors.append(f"{name} 存在重复 id")
        for index, case in enumerate(cases):
            if not isinstance(case, dict) or not case.get("id"):
                errors.append(f"{name} 第 {index + 1} 条缺少 id")
    trigger = payloads.get("trigger_eval_set.json", {}).get("cases", [])
    if sum(bool(case.get("should_trigger")) for case in trigger) < 10:
        errors.append("触发集正例少于 10 条")
    if sum(not bool(case.get("should_trigger")) for case in trigger) < 5:
        errors.append("触发集负例少于 5 条")
    workflow = payloads.get("workflow_eval_set.json", {}).get("cases", [])
    required = {"memory_first", "mcp_probe", "master_guard", "push_confirmation", "revision_run"}
    categories = {case.get("category") for case in workflow}
    errors.extend(f"工作流评估集缺少类别：{item}" for item in sorted(required - categories))
    for case in workflow:
        for path_value in case.get("must_read", []):
            candidate = eval_dir.parents[3] / path_value
            if path_value == ".workbuddy/memory":
                candidate = eval_dir.parents[3] / path_value
                if not candidate.is_dir():
                    errors.append(f"must_read 目录不存在：{path_value}")
            elif not candidate.is_file():
                errors.append(f"must_read 文件不存在：{path_value}")
    return errors


if __name__ == "__main__":
    problems = validate_eval_sets(Path(__file__).resolve().parent)
    if problems:
        for problem in problems:
            print(f"错误：{problem}")
        raise SystemExit(1)
    print("e9-newcomer-guide 评估集校验通过")
