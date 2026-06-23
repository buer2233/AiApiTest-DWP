import json
import re
from pathlib import Path


FAILED_STATUSES = {"failed", "broken"}


def parse_allure_failures(results_dir: str | Path) -> list[dict]:
    root = Path(results_dir)
    if not root.exists() or not root.is_dir():
        return []

    failures = []
    for result_file in sorted(root.glob("*.json")):
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        status = str(payload.get("status") or "unknown")
        if status not in FAILED_STATUSES:
            continue
        failures.append(_failure_from_payload(payload, status))
    return failures


def _failure_from_payload(payload: dict, status: str) -> dict:
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
    if not full_name:
        return ""
    module_name, _, case_name = full_name.partition("#")
    module_path = module_name.replace(".", "/")
    if not module_path.endswith(".py"):
        module_path = f"{module_path}.py"
    return f"{module_path}::{case_name}" if case_name else module_path


def _case_name_from_node_id(node_id: str) -> str:
    return node_id.rsplit("::", 1)[-1] if "::" in node_id else node_id.rsplit("/", 1)[-1]


def _module_path_from_payload(payload: dict, node_id: str) -> str:
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
    source = message or trace
    match = re.match(r"([A-Za-z_][\w.]*Error|[A-Za-z_][\w.]*Exception)", source)
    if match:
        return match.group(1).split(".")[-1]
    return ""
