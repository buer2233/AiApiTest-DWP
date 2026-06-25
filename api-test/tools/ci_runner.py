"""
CI 运行器模块 - Jenkins CI/CD 测试执行核心

负责解析 Jenkins 参数、构建 pytest 命令、执行测试、收集失败用例、
生成 Allure 报告，并输出标准化的 CI 产物供后端和前端消费。

执行命令：
    python -m tools.ci_runner --from-jenkins-env
    python -m tools.ci_runner --case-path test_case/test_gbif_case
    python -m tools.ci_runner --retry-mode all-failed --retry-count 3

产物结构：
    runtime/ci-runs/{run_id}/
    ├── allure-results/      # Allure 原始结果
    ├── allure-report/       # Allure HTML 报告
    ├── console.log          # pytest 执行日志
    ├── failed_nodeids.json  # 失败用例 node id 列表
    └── summary.json         # CI 运行摘要
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tools.pytest_nodeids import load_lastfailed, normalize_nodeids, write_nodeids


# api-test 根目录路径
API_TEST_ROOT = Path(__file__).resolve().parents[1]

# 支持的重试模式
VALID_RETRY_MODES = {"none", "selected", "all-failed", "module"}


@dataclass
class RunRequest:
    """CI 运行请求数据类，封装测试运行所需的所有参数。"""

    api_test_root: Path
    run_dir: Path
    retry_mode: str = "none"
    case_path: str = "test_case"
    node_ids: list[str] = field(default_factory=list)
    retry_count: int = 0
    clean: bool = True
    open_report: bool = False


def build_pytest_command(
    targets: list[str],
    allure_results_dir: Path,
    clean: bool = True,
    retry_count: int = 0,
    python_executable: str = "python",
) -> list[str]:
    """构建 pytest 执行命令。
    Args:
        targets: pytest 测试目标列表（模块路径或 node id）
        allure_results_dir: Allure 结果输出目录
        clean: 是否清理 Allure 结果目录
        retry_count: 失败重试次数
        python_executable: Python 解释器路径
    Returns:
        pytest 命令行参数列表
    Raises:
        ValueError: retry_count 小于 0 时抛出
    """
    if retry_count < 0:
        raise ValueError("retry_count must be greater than or equal to 0")

    command = [
        python_executable,
        "-m",
        "pytest",
        *targets,
        f"--alluredir={Path(allure_results_dir)}",
    ]
    if clean:
        command.append("--clean-alluredir")
    if retry_count > 0:
        command.extend(["--reruns", str(retry_count)])
    return command


def resolve_pytest_targets(request: RunRequest) -> list[str]:
    """根据重试模式解析 pytest 测试目标。
    Args:
        request: CI 运行请求对象
    Returns:
        pytest 测试目标列表
    Raises:
        ValueError: 重试模式无效或 selected 模式缺少 node id 时抛出
    """
    retry_mode = request.retry_mode
    if retry_mode not in VALID_RETRY_MODES:
        raise ValueError(f"Unsupported retry mode: {retry_mode}")

    if retry_mode in {"none", "module"}:
        return normalize_nodeids([request.case_path])
    if retry_mode == "selected":
        nodeids = normalize_nodeids(request.node_ids)
        if not nodeids:
            raise ValueError("retry-mode selected requires at least one --node-id")
        return nodeids
    return load_lastfailed(Path(request.api_test_root) / ".pytest_cache")


def parse_jenkins_node_ids(raw_value: str | None) -> list[str]:
    """解析 Jenkins 文本参数中的 pytest node id（支持换行或逗号分隔）。"""
    if raw_value is None:
        return []
    return normalize_nodeids(re.split(r"[\r\n,]+", str(raw_value)))


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    """解析布尔类型参数，支持 1/true/yes/y/on 等格式。"""
    if raw_value is None or str(raw_value).strip() == "":
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_retry_count(raw_value: str | None) -> int:
    """解析重试次数参数，默认返回 0。"""
    if raw_value is None or str(raw_value).strip() == "":
        return 0
    retry_count = int(str(raw_value).strip())
    if retry_count < 0:
        raise ValueError("retry_count must be greater than or equal to 0")
    return retry_count


def build_run_request_from_jenkins_env(
    env: Mapping[str, str] | None = None,
    api_test_root: Path = API_TEST_ROOT,
) -> RunRequest:
    """从 Jenkins 环境变量构建 CI 运行请求。
    支持的环境变量：RETRY_MODE、RUN_ID/BUILD_TAG/BUILD_NUMBER、
    CASE_PATH、PYTEST_NODE_IDS、RETRY_COUNT、CLEAN_ALLURE、OPEN_REPORT
    Args:
        env: 环境变量字典，默认读取 os.environ
        api_test_root: api-test 根目录路径
    Returns:
        CI 运行请求对象
    Raises:
        ValueError: 重试模式无效时抛出
    """
    source = env or os.environ
    retry_mode = source.get("RETRY_MODE", "none").strip() or "none"
    if retry_mode not in VALID_RETRY_MODES:
        raise ValueError(f"Unsupported retry mode: {retry_mode}")

    run_id = source.get("RUN_ID") or source.get("BUILD_TAG") or source.get("BUILD_NUMBER")
    return RunRequest(
        api_test_root=Path(api_test_root),
        run_dir=build_run_dir(Path(api_test_root), run_id),
        retry_mode=retry_mode,
        case_path=source.get("CASE_PATH", "test_case/test_gbif_case").strip()
        or "test_case/test_gbif_case",
        node_ids=parse_jenkins_node_ids(source.get("PYTEST_NODE_IDS")),
        retry_count=_parse_retry_count(source.get("RETRY_COUNT")),
        clean=_parse_bool(source.get("CLEAN_ALLURE"), True),
        open_report=_parse_bool(source.get("OPEN_REPORT"), False),
    )


def ensure_run_dirs(run_dir: Path) -> None:
    """创建 CI 运行目录结构（allure-results、allure-report）。"""
    for path in [
        run_dir,
        run_dir / "allure-results",
        run_dir / "allure-report",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def clear_lastfailed_cache(api_test_root: Path) -> None:
    """清理 pytest lastfailed 缓存，避免影响本次运行。"""
    cache_file = Path(api_test_root) / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if cache_file.exists():
        cache_file.unlink()


def write_summary(
    run_dir: Path,
    return_code: int,
    failed_nodeids: list[str],
    allure_results_dir: Path,
    allure_report_dir: Path,
    allure_report_status: str = "unknown",
    allure_report_message: str = "",
) -> dict:
    """写入并返回 CI 运行摘要（summary.json）。
    Args:
        run_dir: 运行目录路径
        return_code: pytest 返回码（0 表示成功）
        failed_nodeids: 失败用例 node id 列表
        allure_results_dir: Allure 结果目录
        allure_report_dir: Allure 报告目录
        allure_report_status: 报告生成状态
        allure_report_message: 报告生成消息
    Returns:
        CI 运行摘要字典
    """
    status = "passed" if return_code == 0 else "failed"
    summary = {
        "status": status,
        "return_code": return_code,
        "failed_nodeids": normalize_nodeids(failed_nodeids),
        "allure_results_dir": str(Path(allure_results_dir)),
        "allure_report_dir": str(Path(allure_report_dir)),
        "allure_report_status": allure_report_status,
        "allure_report_message": allure_report_message,
    }
    output_path = Path(run_dir) / "summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _write_console_log(run_dir: Path, result: subprocess.CompletedProcess) -> None:
    """写入 pytest 执行的控制台日志（console.log）。"""
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    content = "\n".join(part for part in [stdout, stderr] if part)
    (Path(run_dir) / "console.log").write_text(content, encoding="utf-8")


def _generate_allure_report(request: RunRequest) -> dict:
    """生成 Allure HTML 报告。

    Returns:
        报告生成结果，包含 status（generated/failed/skipped）和 message
    """
    allure_executable = shutil.which("allure")
    if not allure_executable:
        return {
            "status": "skipped",
            "message": "Allure CLI was not found in PATH; HTML report was not generated.",
        }

    command = [
        allure_executable,
        "generate",
        str(Path(request.run_dir) / "allure-results"),
        "-o",
        str(Path(request.run_dir) / "allure-report"),
        "--clean",
    ]
    result = subprocess.run(
        command,
        cwd=str(request.api_test_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        return {
            "status": "failed",
            "message": message or f"Allure CLI exited with code {result.returncode}.",
        }
    if request.open_report:
        subprocess.run(
            [allure_executable, "open", str(Path(request.run_dir) / "allure-report")],
            cwd=str(request.api_test_root),
            check=False,
        )
    return {
        "status": "generated",
        "message": "Allure HTML report generated successfully.",
    }


def run_ci_tests(request: RunRequest, python_executable: str | None = None) -> dict:
    """执行 CI 测试并生成所有产物。
    执行流程：创建目录 → 解析目标 → 清理缓存 → 执行 pytest → 写入日志 →
    生成 Allure 报告 → 收集失败用例 → 写入摘要
    Args:
        request: CI 运行请求对象
        python_executable: Python 解释器路径，默认使用 sys.executable
    Returns:
        CI 运行摘要字典
    """
    request.api_test_root = Path(request.api_test_root)
    request.run_dir = Path(request.run_dir)
    ensure_run_dirs(request.run_dir)

    targets = resolve_pytest_targets(request)
    allure_results_dir = request.run_dir / "allure-results"
    allure_report_dir = request.run_dir / "allure-report"

    # 无测试目标时直接返回
    if not targets:
        write_nodeids([], request.run_dir / "failed_nodeids.json")
        (request.run_dir / "console.log").write_text("No pytest targets resolved.\n", encoding="utf-8")
        return write_summary(
            run_dir=request.run_dir,
            return_code=0,
            failed_nodeids=[],
            allure_results_dir=allure_results_dir,
            allure_report_dir=allure_report_dir,
            allure_report_status="skipped",
            allure_report_message="No pytest targets resolved; Allure HTML report was not generated.",
        )

    clear_lastfailed_cache(request.api_test_root)
    command = build_pytest_command(
        targets=targets,
        allure_results_dir=allure_results_dir,
        clean=request.clean,
        retry_count=request.retry_count,
        python_executable=python_executable or sys.executable,
    )
    result = subprocess.run(
        command,
        cwd=str(request.api_test_root),
        check=False,
        capture_output=True,
        text=True,
    )
    _write_console_log(request.run_dir, result)
    allure_report = _generate_allure_report(request)

    failed_nodeids = load_lastfailed(request.api_test_root / ".pytest_cache")
    write_nodeids(failed_nodeids, request.run_dir / "failed_nodeids.json")
    return write_summary(
        run_dir=request.run_dir,
        return_code=result.returncode,
        failed_nodeids=failed_nodeids,
        allure_results_dir=allure_results_dir,
        allure_report_dir=allure_report_dir,
        allure_report_status=allure_report["status"],
        allure_report_message=allure_report["message"],
    )


def build_run_dir(api_test_root: Path, run_id: str | None = None) -> Path:
    """构建 CI 运行目录路径（runtime/ci-runs/{run_id}）。"""
    actual_run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(api_test_root) / "runtime" / "ci-runs" / actual_run_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Run api-test pytest cases for CI.")
    parser.add_argument(
        "--from-jenkins-env",
        action="store_true",
        help="read Jenkins parameters from environment variables",
    )
    parser.add_argument("--case-path", default="test_case", help="pytest module or case path")
    parser.add_argument("--node-id", action="append", default=[], help="pytest node id, repeatable")
    parser.add_argument(
        "--retry-mode",
        choices=sorted(VALID_RETRY_MODES),
        default="none",
        help="retry mode: none, selected, all-failed or module",
    )
    parser.add_argument("--retry-count", type=int, default=0, help="pytest-rerunfailures retry count")
    parser.add_argument("--run-id", default=None, help="external run id for runtime/ci-runs")
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="pass --clean-alluredir to pytest",
    )
    parser.add_argument(
        "--open-report",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="open generated Allure HTML report when Allure CLI is installed",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """主入口函数。
    支持两种模式：
    - Jenkins 环境变量模式（--from-jenkins-env 或 CI_RUNNER_ENV=jenkins）
    - 命令行参数模式
    Returns:
        pytest 返回码（0 表示成功）
    """
    args = parse_args(argv)
    if args.from_jenkins_env or os.environ.get("CI_RUNNER_ENV") == "jenkins":
        request = build_run_request_from_jenkins_env(os.environ, api_test_root=API_TEST_ROOT)
        summary = run_ci_tests(request)
        return int(summary["return_code"])

    if args.retry_count < 0:
        raise ValueError("retry_count must be greater than or equal to 0")
    request = RunRequest(
        api_test_root=API_TEST_ROOT,
        run_dir=build_run_dir(API_TEST_ROOT, args.run_id),
        retry_mode=args.retry_mode,
        case_path=args.case_path,
        node_ids=args.node_id,
        retry_count=args.retry_count,
        clean=args.clean,
        open_report=args.open_report,
    )
    summary = run_ci_tests(request)
    return int(summary["return_code"])


if __name__ == "__main__":
    raise SystemExit(main())
