"""安全处理 Allure 失败分析的冻结、校验和回写工具。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from tools.sensitive_data import redact_sensitive_text


ANALYSIS_ATTACHMENT_NAME = "AI 分析"
ALLOWED_CATEGORIES = {
    "environment",
    "credentials_config",
    "dependency",
    "test_data",
    "test_code",
    "product_defect",
    "unknown",
}
ANALYSIS_TEXT_FIELDS = (
    "conclusion",
    "evidence",
    "recommendation",
    "environment_revision_assumption",
)
MAX_ANALYSIS_TEXT_LENGTH = 1_000


class AnalysisValidationError(ValueError):
    """子任务输出不安全或违反分析契约时抛出。"""


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _managed_attachment_for_uuid(attachment: object, result_uuid: str) -> bool:
    if not isinstance(attachment, dict):
        return False
    return (
        attachment.get("name") == ANALYSIS_ATTACHMENT_NAME
        and str(attachment.get("source", "")).startswith(f"ai-analysis-{result_uuid}")
    )


def _integrity_hash(result: dict[str, Any]) -> str:
    """计算原始结果状态哈希，忽略本工具管理的附件。"""
    result_uuid = str(result.get("uuid", ""))
    normalized = dict(result)
    attachments = normalized.get("attachments", [])
    if isinstance(attachments, list):
        normalized["attachments"] = [
            item for item in attachments if not _managed_attachment_for_uuid(item, result_uuid)
        ]
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _redact_failure_text(value: object, limit: int = 2_000) -> str:
    text = redact_sensitive_text(str(value or ""))
    # 账号标识既不能支持分类，也可能属于敏感信息。
    text = re.sub(
        r"(?i)(\b(?:username|user_name|loginid|account)\s*[:=]\s*)[^\s,;}&]+",
        r"\1[REDACTED]",
        text,
    )
    return text[:limit]


def _fingerprint(status: str, error_text: str) -> str:
    normalized = error_text.lower()
    normalized = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27,}", "<uuid>", normalized)
    normalized = re.sub(r"\d+", "#", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    digest = hashlib.sha256(f"{status}:{normalized}".encode("utf-8")).hexdigest()[:20]
    return f"failure-{digest}"


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _failure_record(path: Path, result: dict[str, Any], raw: bytes) -> dict[str, Any]:
    status_details = result.get("statusDetails")
    status_details = status_details if isinstance(status_details, dict) else {}
    error_text = _redact_failure_text(
        "\n".join(
            str(status_details.get(key, "")) for key in ("message", "trace")
        )
    )
    status = str(result.get("status", ""))
    return {
        "path": str(path.resolve()),
        "uuid": str(result.get("uuid", path.stem.removesuffix("-result"))),
        "sha256": _sha256_bytes(raw),
        "integrity_sha256": _integrity_hash(result),
        "status": status,
        "fingerprint": _fingerprint(status, error_text),
        "error": error_text,
    }


def freeze_manifest(run_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    """冻结脱敏失败事实，并为每个指纹创建一个不可变输入。"""
    results = sorted(run_dir.glob("*-result.json"))
    status_counts: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    for result_path in results:
        try:
            raw = result_path.read_bytes()
            result = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(result, dict):
            continue
        status = str(result.get("status", "unknown"))
        status_counts[status] += 1
        if status in {"failed", "broken"}:
            failures.append(_failure_record(result_path, result, raw))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        grouped.setdefault(failure["fingerprint"], []).append(failure)
    shard_dir = run_dir / "ai-analysis-inputs"
    shards: list[dict[str, Any]] = []
    for fingerprint, occurrences in sorted(grouped.items()):
        shard_path = shard_dir / f"{fingerprint}.json"
        shard_payload = {
            "fingerprint": fingerprint,
            "occurrences": [
                {
                    "uuid": item["uuid"],
                    "status": item["status"],
                    "error": item["error"],
                }
                for item in occurrences
            ],
        }
        _atomic_write_json(shard_path, shard_payload)
        shards.append(
            {
                "fingerprint": fingerprint,
                "input_path": str(shard_path.resolve()),
                "occurrence_count": len(occurrences),
            }
        )
    manifest = {
        "schema_version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "run_dir": str(run_dir.resolve()),
        "summary": {
            "total": sum(status_counts.values()),
            "passed": status_counts["passed"],
            "failed": status_counts["failed"],
            "broken": status_counts["broken"],
        },
        "failures": failures,
        "shards": shards,
    }
    _atomic_write_json(manifest_path or run_dir / "ai-analysis-manifest.json", manifest)
    return manifest


def shard_count(manifest: dict[str, Any], available_workers: int) -> int:
    return min(10, len(manifest.get("shards", [])), max(0, available_workers))


def worker_instruction(shard_path: Path) -> str:
    """返回分配分片时必须附带的只读契约。"""
    return (
        "只读取分配的不可变 JSON 文件和 references/allure-analysis.md。"
        "不得读取配置、执行命令、修改文件、访问网络或检查其他路径。"
        f"为以下文件中的每个失败指纹精确返回一个分析 JSON 对象：{shard_path.resolve()}"
    )


def _contains_sensitive_text(value: str) -> bool:
    redacted = _redact_failure_text(value, limit=len(value) + 1)
    return redacted != value


def validate_analysis_results(
    manifest: dict[str, Any], analyses: Iterable[dict[str, Any]]
) -> list[str]:
    """依据冻结清单和安全契约校验子任务输出。"""
    errors: list[str] = []
    allowed_fingerprints = {item["fingerprint"] for item in manifest.get("shards", [])}
    seen: set[str] = set()
    for index, analysis in enumerate(analyses):
        label = f"第 {index} 条分析"
        if not isinstance(analysis, dict):
            errors.append(f"{label} 必须是对象")
            continue
        fingerprint = analysis.get("fingerprint")
        if fingerprint not in allowed_fingerprints:
            errors.append(f"{label} 的 fingerprint 不在清单中")
        elif fingerprint in seen:
            errors.append(f"{label} 重复使用了 fingerprint")
        else:
            seen.add(fingerprint)
        category = analysis.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{label} 的 category 无效")
        confidence = analysis.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{label} 的 confidence 必须是 0 到 1 的数字")
        if not isinstance(analysis.get("needs_human"), bool):
            errors.append(f"{label} 的 needs_human 必须是布尔值")
        for field in ANALYSIS_TEXT_FIELDS:
            value = analysis.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_ANALYSIS_TEXT_LENGTH:
                errors.append(f"{label} 的 {field} 无效")
            elif _contains_sensitive_text(value):
                errors.append(f"{label} 的 {field} 包含敏感文本")
        assumption = str(analysis.get("environment_revision_assumption", ""))
        if category == "product_defect" and "未确认" in assumption:
            errors.append(f"{label} 在环境版本未确认时不得分类为 product_defect")
    return errors


def _render_attachment(analysis: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"类别：{analysis['category']}",
            f"结论：{analysis['conclusion']}",
            f"证据：{analysis['evidence']}",
            f"建议：{analysis['recommendation']}",
            f"置信度：{analysis['confidence']}",
            f"环境前提：{analysis['environment_revision_assumption']}",
            f"需要人工确认：{'是' if analysis['needs_human'] else '否'}",
            "",
        )
    )


def writeback_analysis(
    run_dir: Path, manifest: dict[str, Any], analyses: Iterable[dict[str, Any]]
) -> dict[str, int]:
    """哈希复核后，为每个匹配结果回写一个受管附件。"""
    analysis_list = list(analyses)
    errors = validate_analysis_results(manifest, analysis_list)
    if errors:
        raise AnalysisValidationError("; ".join(errors))
    by_fingerprint = {analysis["fingerprint"]: analysis for analysis in analysis_list}
    written = 0
    stale = 0
    skipped = 0
    summary_entries: list[dict[str, Any]] = []
    for failure in manifest.get("failures", []):
        analysis = by_fingerprint.get(failure["fingerprint"])
        if analysis is None:
            skipped += 1
            continue
        result_path = Path(failure["path"])
        try:
            current_raw = result_path.read_bytes()
            result = json.loads(current_raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            stale += 1
            continue
        if not isinstance(result, dict) or _integrity_hash(result) != failure["integrity_sha256"]:
            stale += 1
            continue
        result_uuid = str(result.get("uuid", failure["uuid"]))
        attachment_name = f"ai-analysis-{result_uuid}.txt"
        _atomic_write_text(run_dir / attachment_name, _render_attachment(analysis))
        attachments = result.get("attachments")
        attachments = attachments if isinstance(attachments, list) else []
        result["attachments"] = [
            item for item in attachments if not _managed_attachment_for_uuid(item, result_uuid)
        ]
        result["attachments"].append(
            {"name": ANALYSIS_ATTACHMENT_NAME, "source": attachment_name, "type": "text/plain"}
        )
        _atomic_write_json(result_path, result)
        written += 1
        summary_entries.append(
            {
                "fingerprint": analysis["fingerprint"],
                "category": analysis["category"],
                "conclusion": analysis["conclusion"],
                "recommendation": analysis["recommendation"],
                "confidence": analysis["confidence"],
                "needs_human": analysis["needs_human"],
            }
        )
    _atomic_write_json(
        run_dir / "ai-analysis-summary.json",
        {"written": written, "stale": stale, "skipped": skipped, "analyses": summary_entries},
    )
    return {"written": written, "stale": stale, "skipped": skipped}


def rebuild_allure_report(run_dir: Path, report_root: Path | None = None) -> Path | None:
    """生成新的带时间戳 HTML 报告；Allure 失败时返回 None。"""
    output_root = report_root or run_dir.parent / "allure-report"
    output_dir = output_root / time.strftime("%Y%m%d_%H%M%S")
    allure_cli = shutil.which("allure")
    if not allure_cli:
        return None
    try:
        completed = subprocess.run(
            [allure_cli, "generate", str(run_dir), "-o", str(output_dir), "--clean"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None
    return output_dir if completed.returncode == 0 else None


def _load_analysis_payload(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("analyses"), list):
        return payload["analyses"]
    raise AnalysisValidationError("分析文件必须是数组或包含 analyses 的对象")


def main() -> int:
    parser = argparse.ArgumentParser(description="准备并回写 Allure AI 分析。")
    subparsers = parser.add_subparsers(dest="action", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--run-dir", required=True, type=Path)
    writeback_parser = subparsers.add_parser("writeback")
    writeback_parser.add_argument("--run-dir", required=True, type=Path)
    writeback_parser.add_argument("--manifest", required=True, type=Path)
    writeback_parser.add_argument("--analysis", required=True, type=Path)
    rebuild_parser = subparsers.add_parser("rebuild")
    rebuild_parser.add_argument("--run-dir", required=True, type=Path)
    rebuild_parser.add_argument("--report-root", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        manifest = freeze_manifest(args.run_dir)
        print(json.dumps({"failures": len(manifest["failures"]), "shards": len(manifest["shards"])}))
        return 0
    if args.action == "writeback":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        try:
            outcome = writeback_analysis(args.run_dir, manifest, _load_analysis_payload(args.analysis))
        except AnalysisValidationError as exc:
            print(f"分析结果被拒绝：{exc}")
            return 1
        print(json.dumps(outcome))
        return 0
    report = rebuild_allure_report(args.run_dir, args.report_root)
    if report is None:
        print("Allure 报告生成失败")
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
