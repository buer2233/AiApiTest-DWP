"""环境目录同步 Job 对 Task 1 YAML 校验和确定性序列化的薄适配器。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "api-test"))

from tools.environment_catalog import (  # noqa: E402
    dump_environment_catalog,
    git_blob_sha,
    load_environment_catalog,
    verify_yaml_blob_sha,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_catalog(args: argparse.Namespace) -> None:
    """在写 YAML 前校验当前 blob SHA，再写入冻结快照的确定性目录。"""
    yaml_path = Path(args.yaml_path)
    observed_blob_sha = verify_yaml_blob_sha(
        yaml_path.read_text(encoding="utf-8"), args.expected_blob_sha
    )
    payload = json.loads(Path(args.catalog_json).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("catalog_json must contain an environment mapping.")
    serialized = dump_environment_catalog(payload)
    yaml_path.write_text(serialized, encoding="utf-8")
    _write_json(
        Path(args.result_path),
        {
            "direction": "mysql_to_yaml",
            "expected_yaml_blob_sha": args.expected_blob_sha,
            "observed_yaml_blob_sha": observed_blob_sha,
            "written_yaml_blob_sha": git_blob_sha(serialized),
        },
    )


def import_catalog(args: argparse.Namespace) -> None:
    """解析隔离 checkout 的 YAML，并导出供受限内部回调消费的规范化快照。"""
    yaml_path = Path(args.yaml_path)
    content = yaml_path.read_text(encoding="utf-8")
    observed_blob_sha = git_blob_sha(content)
    if args.expected_blob_sha:
        verify_yaml_blob_sha(content, args.expected_blob_sha)
    _write_json(
        Path(args.result_path),
        {
            "direction": "yaml_to_mysql",
            "expected_yaml_blob_sha": args.expected_blob_sha or None,
            "observed_yaml_blob_sha": observed_blob_sha,
            "catalog": load_environment_catalog(yaml_path),
        },
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage13 environment catalog Task 1 adapter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--catalog-json", required=True)
    export_parser.add_argument("--yaml-path", required=True)
    export_parser.add_argument("--expected-blob-sha", required=True)
    export_parser.add_argument("--result-path", required=True)
    export_parser.set_defaults(handler=export_catalog)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--yaml-path", required=True)
    import_parser.add_argument("--expected-blob-sha", default="")
    import_parser.add_argument("--result-path", required=True)
    import_parser.set_defaults(handler=import_catalog)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
