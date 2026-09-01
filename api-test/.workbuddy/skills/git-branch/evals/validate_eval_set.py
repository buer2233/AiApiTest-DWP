"""静态校验 git-branch 的触发集和工作流契约集。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_WORKFLOW_CATEGORIES = {
    "switch_existing",
    "create_new",
    "default_fallback",
    "refuse_no_change",
    "dirty_workdir",
    "invalid_name",
    "query_only",
    "negative",
}
TRIGGER_REQUIRED_KEYS = {"id", "query", "should_trigger"}
WORKFLOW_REQUIRED_KEYS = {
    "id",
    "category",
    "branch",
    "prompt",
    "expected_trigger",
    "expected_stage",
    "must_read",
    "expected_outputs",
    "must",
    "must_not",
}
MIN_POSITIVE_CASES = 11
MIN_NEGATIVE_CASES = 7


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"缺少必需评估文件：{path.name}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name} 中的 JSON 无效：{exc.msg}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.name} 必须是 JSON 对象")
        return None
    return payload


def _require_string(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} 必须是非空字符串")


def _validate_case_list(
    payload: dict[str, Any],
    file_name: str,
    required_keys: set[str],
    errors: list[str],
) -> list[dict[str, Any]]:
    if payload.get("schema_version") != 1:
        errors.append(f"{file_name} 的 schema_version 必须为 1")
    if payload.get("skill_name") != "git-branch":
        errors.append(f"{file_name} 的 skill_name 必须为 git-branch")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{file_name} 的 cases 必须是非空数组")
        return []

    valid_cases: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        label = f"{file_name} 的第 {index} 条用例"
        if not isinstance(case, dict):
            errors.append(f"{label} 必须是对象")
            continue
        missing = required_keys.difference(case)
        if missing:
            errors.append(f"{label} 缺少字段：{', '.join(sorted(missing))}")
            continue
        valid_cases.append(case)
    return valid_cases


def _check_unique_ids(cases: list[dict[str, Any]], label: str, errors: list[str]) -> None:
    ids: list[str] = []
    for index, case in enumerate(cases):
        case_id = case.get("id")
        _require_string(case_id, f"{label} 的第 {index} 条用例 ID", errors)
        if isinstance(case_id, str):
            ids.append(case_id)
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    for duplicate in duplicates:
        errors.append(f"重复 {label} 用例 ID：{duplicate}")


def _candidate_roots(eval_dir: Path) -> list[Path]:
    skill_dir = eval_dir.parent
    api_root = skill_dir.parents[2]
    workspace_root = api_root.parent
    return [skill_dir, api_root, workspace_root]


def _must_read_exists(path_value: str, roots: list[Path]) -> bool:
    relative_path = Path(path_value)
    return any((root / relative_path).is_file() for root in roots)


def _validate_trigger_cases(cases: list[dict[str, Any]], errors: list[str]) -> None:
    _check_unique_ids(cases, "trigger", errors)
    positive_count = 0
    negative_count = 0
    for index, case in enumerate(cases):
        label = f"触发集第 {index} 条用例"
        _require_string(case.get("query"), f"{label} query", errors)
        if not isinstance(case.get("should_trigger"), bool):
            errors.append(f"{label} 的 should_trigger 必须是布尔值")
            continue
        if case["should_trigger"]:
            positive_count += 1
        else:
            negative_count += 1
    if positive_count < MIN_POSITIVE_CASES:
        errors.append(f"触发评估集至少需要 {MIN_POSITIVE_CASES} 条正例")
    if negative_count < MIN_NEGATIVE_CASES:
        errors.append(f"触发评估集至少需要 {MIN_NEGATIVE_CASES} 条负例")


def _validate_workflow_cases(
    cases: list[dict[str, Any]], eval_dir: Path, errors: list[str]
) -> None:
    _check_unique_ids(cases, "workflow", errors)
    categories: set[str] = set()
    roots = _candidate_roots(eval_dir)
    for index, case in enumerate(cases):
        label = f"工作流第 {index} 条用例"
        for key in ("category", "branch", "prompt", "expected_stage"):
            _require_string(case.get(key), f"{label} {key}", errors)
        if isinstance(case.get("category"), str):
            categories.add(case["category"])
        if not isinstance(case.get("expected_trigger"), bool):
            errors.append(f"{label} 的 expected_trigger 必须是布尔值")
        for key in ("must_read", "expected_outputs", "must", "must_not"):
            value = case.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                errors.append(f"{label} 的 {key} 必须是非空字符串数组")
        for read_path in case.get("must_read", []):
            if isinstance(read_path, str) and not _must_read_exists(read_path, roots):
                errors.append(f"{label} 的 must_read 路径不存在：{read_path}")
    missing_categories = REQUIRED_WORKFLOW_CATEGORIES.difference(categories)
    if missing_categories:
        errors.append(
            "工作流评估集缺少类别：" + ", ".join(sorted(missing_categories))
        )


def validate_eval_sets(eval_dir: Path) -> list[str]:
    """返回 *eval_dir* 内评估资产的全部静态校验错误。"""
    errors: list[str] = []
    trigger_payload = _read_json(eval_dir / "trigger_eval_set.json", errors)
    workflow_payload = _read_json(eval_dir / "workflow_eval_set.json", errors)
    if trigger_payload is not None:
        trigger_cases = _validate_case_list(
            trigger_payload, "trigger_eval_set.json", TRIGGER_REQUIRED_KEYS, errors
        )
        _validate_trigger_cases(trigger_cases, errors)
    if workflow_payload is not None:
        workflow_cases = _validate_case_list(
            workflow_payload, "workflow_eval_set.json", WORKFLOW_REQUIRED_KEYS, errors
        )
        _validate_workflow_cases(workflow_cases, eval_dir, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 git-branch 评估资产。")
    parser.add_argument(
        "--eval-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="包含 trigger_eval_set.json 和 workflow_eval_set.json 的目录。",
    )
    args = parser.parse_args()
    errors = validate_eval_sets(args.eval_dir.resolve())
    if errors:
        for error in errors:
            print(f"错误：{error}")
        return 1
    print("git-branch 评估集校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
