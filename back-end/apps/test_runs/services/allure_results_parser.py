"""Allure 结果解析模块。
本模块从 api-test 生成的 Allure result JSON 中提取失败用例摘要。
解析结果会写入 FailureCase，供前端失败用例弹窗和后续失败重试使用。
"""

import json
import re
from pathlib import Path


# Allure 中 failed 和 broken 都代表需要进入失败用例列表的异常结果。
FAILED_STATUSES = {"failed", "broken"}


def parse_allure_failures(results_dir: str | Path) -> list[dict]:
    """解析 Allure 结果目录中的失败用例。
    Args:
        results_dir: Allure 原始结果目录，通常为 `allure-results`。
    Returns:
        list[dict]: 标准化后的失败用例字典列表。
    """
    root = Path(results_dir)
    if not root.exists() or not root.is_dir():
        return []

    failures = []
    for result_file in sorted(root.glob("*.json")):
        try:
            # 单个损坏的 Allure JSON 不应影响整次任务登记，直接跳过该文件。
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        status = str(payload.get("status") or "unknown")
        if status not in FAILED_STATUSES:
            continue
        failures.append(_failure_from_payload(payload, status))
    return failures


def _failure_from_payload(payload: dict, status: str) -> dict:
    """从单个 Allure result payload 构造失败用例摘要。
    Args:
        payload: Allure 单个用例结果 JSON。
        status: 已确认需要记录的 Allure 状态。
    Returns:
        dict: FailureCase 创建所需的标准字段。
    """
    full_name = str(payload.get("fullName") or payload.get("name") or "")
    node_id = _to_pytest_node_id(full_name)
    status_details = payload.get("statusDetails") or {}
    message = str(status_details.get("message") or "")
    return {
        "node_id": node_id,
        "case_name": str(payload.get("name") or _case_name_from_node_id(node_id)),
        "module_path": _module_path_from_payload(payload, node_id),
        "description": str(payload.get("description") or ""),
        "error_type": _error_type(message, str(status_details.get("trace") or "")),
        "assertion_message": message,
        "status": status,
    }


def _to_pytest_node_id(full_name: str) -> str:
    """将 Allure fullName 转换为 pytest node id。
    Args:
        full_name: Allure 记录的完整用例名，如 `pkg.module#test_case`。
    Returns:
        str: pytest 可直接重跑的 node id。
    """
    if not full_name:
        return ""
    module_name, _, case_name = full_name.partition("#")
    module_path = module_name.replace(".", "/")
    if not module_path.endswith(".py"):
        module_path = f"{module_path}.py"
    return f"{module_path}::{case_name}" if case_name else module_path


def _case_name_from_node_id(node_id: str) -> str:
    """从 pytest node id 中提取用例名。"""
    return node_id.rsplit("::", 1)[-1] if "::" in node_id else node_id.rsplit("/", 1)[-1]


def _module_path_from_payload(payload: dict, node_id: str) -> str:
    """从 Allure label 或 pytest node id 中提取模块路径。
    Args:
        payload: Allure 单个用例结果 JSON。
        node_id: 已转换的 pytest node id。
    Returns:
        str: 用例所属模块路径。
    """
    for label in payload.get("labels") or []:
        if label.get("name") in {"suite", "package"} and label.get("value"):
            return str(label["value"]).replace(".", "/")
    if "/" not in node_id:
        return ""
    parts = node_id.split("/")
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1])


def _error_type(message: str, trace: str) -> str:
    """从错误消息或堆栈中提取异常类型。
    Args:
        message: Allure statusDetails.message。
        trace: Allure statusDetails.trace。
    Returns:
        str: 异常类名；无法识别时返回空字符串。
    """
    source = message or trace
    match = re.match(r"([A-Za-z_][\w.]*Error|[A-Za-z_][\w.]*Exception)", source)
    if match:
        return match.group(1).split(".")[-1]
    return ""
