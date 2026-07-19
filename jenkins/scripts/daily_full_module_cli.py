"""Daily 父 Pipeline 对 Task 1 环境目录和聚合协议的薄适配器。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "api-test"))

import config  # noqa: E402
from tools.daily_aggregation import (  # noqa: E402
    DailyWorkerArtifact,
    aggregate_daily_run,
    load_module_keys,
)
from tools.environment_catalog import load_environment_catalog  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def preflight(args: argparse.Namespace) -> None:
    """读取唯一模块清单和环境目录，拒绝未登记的非空目标 URL。"""
    module_keys = load_module_keys(args.module_manifest)
    catalog = load_environment_catalog(args.environment_catalog)
    raw_target = (args.target_base_url or "").strip()
    target_base_url = None
    if raw_target:
        target_base_url = config.validate_base_url(raw_target)
        if target_base_url not in {item["base_url"] for item in catalog.values()}:
            raise ValueError("TARGET_BASE_URL must match a registered environment.")
    _write_json(
        Path(args.output),
        {
            "module_keys": module_keys,
            "target_base_url": target_base_url,
        },
    )


def aggregate(args: argparse.Namespace) -> None:
    """将 Jenkins 已回收的 Worker 归档交给 Task 1 聚合器。"""
    raw_artifacts = json.loads(Path(args.worker_artifacts).read_text(encoding="utf-8"))
    if not isinstance(raw_artifacts, list):
        raise ValueError("worker_artifacts must be a JSON list.")
    artifacts = [
        DailyWorkerArtifact(module_key=item["module_key"], run_dir=Path(item["run_dir"]))
        for item in raw_artifacts
    ]
    aggregate_daily_run(args.module_manifest, artifacts, args.parent_run_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13 Daily Task 1 adapter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--module-manifest", required=True)
    preflight_parser.add_argument("--environment-catalog", required=True)
    preflight_parser.add_argument("--target-base-url", default="")
    preflight_parser.add_argument("--output", required=True)
    preflight_parser.set_defaults(handler=preflight)

    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--module-manifest", required=True)
    aggregate_parser.add_argument("--worker-artifacts", required=True)
    aggregate_parser.add_argument("--parent-run-dir", required=True)
    aggregate_parser.set_defaults(handler=aggregate)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
