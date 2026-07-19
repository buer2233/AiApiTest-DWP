"""Daily 父运行目录聚合工具，不复制 pytest 执行或失败重试逻辑。"""

import json
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from tools.pytest_nodeids import normalize_nodeids


VALID_WORKER_STATUSES = {"passed", "failed"}


class DailyAggregationError(ValueError):
    """Daily 聚合预检失败时提供稳定、脱敏的机器可读诊断。"""

    def __init__(self, code: str, message: str, **context):
        super().__init__(message)
        self.diagnostic = {"code": code, "message": message, **context}


class _DuplicateModuleKeyError(yaml.YAMLError):
    """显式拒绝 YAML 默认会静默覆盖的重复模块键。"""


class _UniqueModuleKeyLoader(yaml.SafeLoader):
    """为模块清单保留重复 key 诊断。"""


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateModuleKeyError(f"duplicate yaml key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueModuleKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class DailyWorkerArtifact:
    """Daily Worker 归档输入，模块键由父编排器显式绑定。"""

    module_key: str
    run_dir: Path


def load_module_keys(module_manifest_path: str | Path) -> list[str]:
    """从唯一权威模块清单读取全量模块键，并在聚合前完成预检。"""
    try:
        payload = yaml.load(
            Path(module_manifest_path).read_text(encoding="utf-8"), Loader=_UniqueModuleKeyLoader
        )
    except FileNotFoundError as exc:
        raise DailyAggregationError("module_manifest_not_found", "模块清单文件不存在。") from exc
    except _DuplicateModuleKeyError as exc:
        raise DailyAggregationError("duplicate_module_key", "模块清单包含重复模块键。") from exc
    except yaml.YAMLError as exc:
        raise DailyAggregationError("invalid_module_manifest", "模块清单 YAML 格式不合法。") from exc

    if payload is None or payload == {}:
        raise DailyAggregationError("empty_module_manifest", "模块清单不能为空。")
    if not isinstance(payload, Mapping):
        raise DailyAggregationError("invalid_module_manifest", "模块清单顶层必须是 mapping。")

    module_keys = []
    for module_key in payload:
        if not isinstance(module_key, str) or not module_key.strip():
            raise DailyAggregationError("invalid_module_key", "模块清单包含非法模块键。")
        normalized_key = module_key.strip()
        if (
            normalized_key != module_key
            or normalized_key in {".", ".."}
            or "/" in normalized_key
            or "\\" in normalized_key
            or Path(normalized_key).is_absolute()
            or Path(normalized_key).drive
        ):
            raise DailyAggregationError("invalid_module_key", "模块键不能包含路径语义。")
        module_keys.append(normalized_key)
    return sorted(module_keys)


def _parent_child_path(parent_dir: Path, child_name: str) -> Path:
    """确保父归档写入目标始终位于 parent_run_dir 内。"""
    candidate = (parent_dir / child_name).resolve()
    try:
        candidate.relative_to(parent_dir.resolve())
    except ValueError as exc:
        raise DailyAggregationError("invalid_module_key", "模块键不能写出父运行目录。") from exc
    return candidate


def _load_worker_summary(artifact: DailyWorkerArtifact) -> dict:
    """读取并校验 Worker 稳定摘要，不让坏归档覆盖父级已存在数据。"""
    try:
        payload = json.loads((Path(artifact.run_dir) / "summary.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DailyAggregationError(
            "missing_worker_summary", "模块 Worker 缺少 summary.json。", module_key=artifact.module_key
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker summary.json 不可解析。", module_key=artifact.module_key
        ) from exc

    required_fields = {
        "status",
        "return_code",
        "failed_nodeids",
        "total_count",
        "passed_count",
        "failed_count",
        "error_count",
        "skipped_count",
    }
    if not isinstance(payload, dict) or required_fields - set(payload):
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker summary.json 缺少稳定字段。", module_key=artifact.module_key
        )
    if not isinstance(payload["failed_nodeids"], list):
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker failed_nodeids 必须是列表。", module_key=artifact.module_key
        )
    if not all(isinstance(node_id, str) for node_id in payload["failed_nodeids"]):
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker failed_nodeids 元素必须是字符串。", module_key=artifact.module_key
        )
    if normalize_nodeids(payload["failed_nodeids"]) != payload["failed_nodeids"]:
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker failed_nodeids 必须非空、去空白且不重复。", module_key=artifact.module_key
        )
    status = payload["status"]
    if not isinstance(status, str) or status not in VALID_WORKER_STATUSES:
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker status 非法。", module_key=artifact.module_key
        )
    if status == "passed" and payload["failed_nodeids"]:
        raise DailyAggregationError(
            "invalid_worker_summary", "通过的模块 Worker 不能包含 failed_nodeids。", module_key=artifact.module_key
        )
    return_code = payload["return_code"]
    if type(return_code) is not int:
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker return_code 必须是整数。", module_key=artifact.module_key
        )
    if (status == "passed" and return_code != 0) or (status == "failed" and return_code == 0):
        raise DailyAggregationError(
            "invalid_worker_summary", "模块 Worker status 与 return_code 不一致。", module_key=artifact.module_key
        )
    for field_name in {"total_count", "passed_count", "failed_count", "error_count", "skipped_count"}:
        if not isinstance(payload[field_name], int) or payload[field_name] < 0:
            raise DailyAggregationError(
                "invalid_worker_summary", "模块 Worker 统计字段必须是非负整数。", module_key=artifact.module_key
            )
    allure_results_dir = Path(artifact.run_dir) / "allure-results"
    if not allure_results_dir.is_dir():
        raise DailyAggregationError(
            "missing_allure_results", "模块 Worker 缺少 Allure 原始结果。", module_key=artifact.module_key
        )
    return payload


def _build_module_detail(module_key: str, summary: Mapping) -> dict:
    """将 Worker 摘要收敛为不暴露宿主机绝对路径的模块明细。"""
    return {
        "module_key": module_key,
        "status": summary["status"],
        "return_code": summary["return_code"],
        "total_count": summary["total_count"],
        "passed_count": summary["passed_count"],
        "failed_count": summary["failed_count"],
        "error_count": summary["error_count"],
        "skipped_count": summary["skipped_count"],
        "failed_nodeids": list(summary["failed_nodeids"]),
        "case_results": list(summary.get("case_results", [])),
    }


def _write_json(path: Path, payload: Mapping) -> None:
    """以确定性 JSON 保存父级可归档产物。"""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def aggregate_daily_run(
    module_manifest_path: str | Path,
    worker_artifacts: Iterable[DailyWorkerArtifact],
    parent_run_dir: str | Path,
) -> dict:
    """汇总全部 Worker 结果、模块明细和 Allure 原始结果到单一父运行目录。"""
    module_keys = load_module_keys(module_manifest_path)
    artifacts = list(worker_artifacts)
    artifact_by_module: dict[str, DailyWorkerArtifact] = {}
    for artifact in artifacts:
        module_key = artifact.module_key
        if module_key in artifact_by_module:
            raise DailyAggregationError(
                "duplicate_module_detail", "父归档包含重复模块明细。", module_key=module_key
            )
        artifact_by_module[module_key] = artifact

    unknown_modules = sorted(set(artifact_by_module) - set(module_keys))
    if unknown_modules:
        raise DailyAggregationError(
            "unknown_module_detail", "父归档包含模块清单外的模块明细。", modules=unknown_modules
        )
    missing_modules = [module_key for module_key in module_keys if module_key not in artifact_by_module]
    if missing_modules:
        raise DailyAggregationError(
            "missing_module_details", "父归档缺少模块明细。", modules=missing_modules
        )

    summaries = {
        module_key: _load_worker_summary(artifact_by_module[module_key]) for module_key in module_keys
    }
    parent_dir = Path(parent_run_dir)
    if parent_dir.exists() and any(parent_dir.iterdir()):
        raise DailyAggregationError(
            "existing_parent_artifact", "父运行目录已存在归档，拒绝覆盖。"
        )

    details = [_build_module_detail(module_key, summaries[module_key]) for module_key in module_keys]
    failed_nodeids = sorted(
        {
            node_id
            for detail in details
            for node_id in detail["failed_nodeids"]
            if isinstance(node_id, str) and node_id
        }
    )
    parent_summary = {
        "status": "passed" if all(detail["status"] == "passed" for detail in details) else "failed",
        "module_count": len(details),
        "total_count": sum(detail["total_count"] for detail in details),
        "passed_count": sum(detail["passed_count"] for detail in details),
        "failed_count": sum(detail["failed_count"] for detail in details),
        "error_count": sum(detail["error_count"] for detail in details),
        "skipped_count": sum(detail["skipped_count"] for detail in details),
        "failed_nodeids": failed_nodeids,
        "allure_results_dir": "allure-results",
        "module_details_dir": "module-details",
        "modules": details,
        "diagnostics": [],
    }

    details_dir = parent_dir / "module-details"
    allure_results_dir = parent_dir / "allure-results"
    parent_dir.mkdir(parents=True, exist_ok=True)
    details_dir.mkdir(exist_ok=True)
    allure_results_dir.mkdir(exist_ok=True)
    for detail in details:
        module_key = detail["module_key"]
        _write_json(_parent_child_path(details_dir, f"{module_key}.json"), detail)
        destination = _parent_child_path(allure_results_dir, module_key)
        shutil.copytree(Path(artifact_by_module[module_key].run_dir) / "allure-results", destination)
    _write_json(parent_dir / "summary.json", parent_summary)
    return parent_summary
