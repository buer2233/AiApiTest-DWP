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
import signal
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import config

from tools.environment_catalog import load_environment_catalog
from tools.pytest_nodeids import load_lastfailed, normalize_nodeids, write_nodeids
from tools.sensitive_data import redact_sensitive_text


# api-test 根目录路径
API_TEST_ROOT = Path(__file__).resolve().parents[1]

# Jenkins CI 中单个模块不应无限运行；超时后仍写 summary 供平台诊断。
DEFAULT_PYTEST_TIMEOUT_SECONDS = 45 * 60
DEFAULT_ALLURE_TIMEOUT_SECONDS = 10 * 60
DEFAULT_CI_RUN_RETENTION_DAYS = 30
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

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
    pytest_timeout_seconds: int = DEFAULT_PYTEST_TIMEOUT_SECONDS
    allure_timeout_seconds: int = DEFAULT_ALLURE_TIMEOUT_SECONDS
    retention_days: int = DEFAULT_CI_RUN_RETENTION_DAYS
    base_url: str | None = None


def build_pytest_command(
    targets: list[str],
    allure_results_dir: Path,
    clean: bool = True,
    retry_count: int = 0,
    python_executable: str = "python",
    base_url: str | None = None,
) -> list[str]:
    """构建 pytest 执行命令。
    Args:
        targets: pytest 测试目标列表（模块路径或 node id）
        allure_results_dir: Allure 结果输出目录
        clean: 是否清理 Allure 结果目录
        retry_count: 失败重试次数
        python_executable: Python 解释器路径
        base_url: 已校验的目标环境 URL；为空时沿用 config.py 私有默认值
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
        "-vv",
        *targets,
        f"--alluredir={Path(allure_results_dir)}",
        "-p",
        "tools.pytest_case_reporter",
        f"--ci-case-results={Path(allure_results_dir).parent / 'case_results.json'}",
        "-o",
        f"cache_dir={Path(allure_results_dir).parent / '.pytest_cache'}",
    ]
    if clean:
        command.append("--clean-alluredir")
    if retry_count > 0:
        command.extend(["--reruns", str(retry_count)])
    if base_url:
        command.extend(["--base-url", config.validate_base_url(base_url)])
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
    latest_failed = load_latest_failed_nodeids(request.api_test_root)
    if latest_failed is not None:
        return latest_failed
    return load_lastfailed(Path(request.api_test_root) / ".pytest_cache")


def load_latest_failed_nodeids(api_test_root: Path) -> list[str] | None:
    """读取最近一次有效 CI run 的失败 node id；没有有效产物时返回 None。"""
    ci_runs_dir = Path(api_test_root) / "runtime" / "ci-runs"
    if not ci_runs_dir.exists():
        return None
    try:
        runs = sorted(
            (entry for entry in ci_runs_dir.iterdir() if entry.is_dir() and not entry.is_symlink()),
            key=lambda entry: entry.stat().st_mtime,
            reverse=True,
        )
    except FileNotFoundError:
        return None
    for run_dir in runs:
        try:
            payload = json.loads((run_dir / "failed_nodeids.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, list):
            return normalize_nodeids(payload)
    return None


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


def _parse_retention_days(raw_value: str | None) -> int:
    """解析 CI 运行目录保留天数；非法值回退到默认 30 天。"""
    if raw_value is None or str(raw_value).strip() == "":
        return DEFAULT_CI_RUN_RETENTION_DAYS
    try:
        retention_days = int(str(raw_value).strip())
    except ValueError:
        return DEFAULT_CI_RUN_RETENTION_DAYS
    if retention_days < 0:
        return DEFAULT_CI_RUN_RETENTION_DAYS
    return retention_days


def _normalize_optional_base_url(raw_value: str | None) -> str | None:
    """规范化可选 URL；空值保留为 None 以继续使用私有默认配置。"""
    if raw_value is None or not str(raw_value).strip():
        return None
    return config.validate_base_url(str(raw_value).strip())


def _validate_jenkins_target_base_url(raw_value: str | None, api_test_root: Path) -> str | None:
    """仅允许 Jenkins 使用环境目录中已登记的非空目标 URL。"""
    target_base_url = _normalize_optional_base_url(raw_value)
    if target_base_url is None:
        return None
    catalog = load_environment_catalog(Path(api_test_root) / "utils" / "package_environment.yaml")
    registered_urls = {environment["base_url"] for environment in catalog.values()}
    if target_base_url not in registered_urls:
        raise ValueError("TARGET_BASE_URL must match a registered environment.")
    return target_base_url


def parse_pytest_summary_counts(console_output: str) -> dict[str, int | float]:
    """从 pytest 控制台最终摘要中解析统计字段。

    pytest 的 Jenkins 返回码在本项目中不直接决定 Pipeline 成败，因此 summary 需要
    携带可供平台同步快照使用的总数、失败数、通过数、跳过数和执行耗时。
    """
    summary_line = ""
    for line in console_output.splitlines():
        lowered = line.lower()
        if " in " in lowered and any(word in lowered for word in ["passed", "failed", "error", "skipped"]):
            summary_line = line
    if not summary_line:
        return {
            "total_count": 0,
            "failed_count": 0,
            "error_count": 0,
            "passed_count": 0,
            "skipped_count": 0,
            "duration_seconds": 0.0,
        }

    counts = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
    }
    for raw_count, raw_status in re.findall(r"(\d+)\s+(passed|failed|errors?|skipped)", summary_line, re.IGNORECASE):
        status_name = raw_status.lower()
        normalized = "error" if status_name in {"error", "errors"} else status_name
        counts[normalized] += int(raw_count)
    duration_match = re.search(r"in\s+([0-9]+(?:\.[0-9]+)?)s", summary_line, re.IGNORECASE)
    duration_seconds = float(duration_match.group(1)) if duration_match else 0.0
    failed_count = counts["failed"] + counts["error"]
    total_count = counts["passed"] + failed_count + counts["skipped"]
    return {
        "total_count": total_count,
        "failed_count": failed_count,
        "error_count": counts["error"],
        "passed_count": counts["passed"],
        "skipped_count": counts["skipped"],
        "duration_seconds": duration_seconds,
    }


def build_run_request_from_jenkins_env(
    env: Mapping[str, str] | None = None,
    api_test_root: Path = API_TEST_ROOT,
) -> RunRequest:
    """从 Jenkins 环境变量构建 CI 运行请求。
    支持的环境变量：RETRY_MODE、RUN_ID/BUILD_TAG/BUILD_NUMBER、
    CASE_PATH、PYTEST_NODE_IDS、RETRY_COUNT、CLEAN_ALLURE、OPEN_REPORT、TARGET_BASE_URL
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
        # Jenkins 非交互环境不能执行 allure open，否则 Allure Web server 会常驻并卡住 Pipeline。
        open_report=False,
        retention_days=_parse_retention_days(source.get("CI_RUN_RETENTION_DAYS")),
        base_url=_validate_jenkins_target_base_url(source.get("TARGET_BASE_URL"), Path(api_test_root)),
    )


def ensure_run_dirs(run_dir: Path) -> None:
    """创建 CI 运行目录结构（allure-results、allure-report）。"""
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(f"CI run directory already exists: {run_dir}") from exc
    (run_dir / "allure-results").mkdir()
    (run_dir / "allure-report").mkdir()


def clear_lastfailed_cache(api_test_root: Path) -> None:
    """清理 pytest lastfailed 缓存，避免影响本次运行。"""
    cache_file = Path(api_test_root) / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if cache_file.exists():
        cache_file.unlink()


def cleanup_old_ci_runs(
    api_test_root: Path,
    current_run_dir: Path,
    retention_days: int = DEFAULT_CI_RUN_RETENTION_DAYS,
    now: float | None = None,
) -> list[Path]:
    """清理超过保留期的历史 CI 运行目录。

    仅处理 `api-test/runtime/ci-runs` 的直接子目录，且永远跳过当前运行目录，
    避免 Jenkins 执行中误删本次 Allure 结果或其它非运行产物。
    """
    ci_runs_dir = Path(api_test_root) / "runtime" / "ci-runs"
    if not ci_runs_dir.exists():
        return []

    cutoff = (now if now is not None else time.time()) - retention_days * 24 * 60 * 60
    current_resolved = Path(current_run_dir).resolve()
    removed: list[Path] = []
    for entry in ci_runs_dir.iterdir():
        # 只删除 run 目录；普通文件和符号链接保留，避免越界清理。
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.resolve() == current_resolved:
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry)
                removed.append(entry)
        except FileNotFoundError:
            # 其它 executor 可能已经完成同一过期目录的清理。
            continue
    return removed


def write_summary(
    run_dir: Path,
    return_code: int,
    failed_nodeids: list[str],
    allure_results_dir: Path,
    allure_report_dir: Path,
    allure_report_status: str = "unknown",
    allure_report_message: str = "",
    count_fields: dict[str, int | float] | None = None,
    case_results: list[dict] | None = None,
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
        "case_results": list(case_results or []),
        "error_count": 0,
    }
    if count_fields:
        summary.update(count_fields)
    output_path = Path(run_dir) / "summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _write_console_log(run_dir: Path, result: subprocess.CompletedProcess) -> None:
    """写入 pytest 执行的控制台日志（console.log）。"""
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    content = redact_sensitive_text("\n".join(part for part in [stdout, stderr] if part))
    (Path(run_dir) / "console.log").write_text(content, encoding="utf-8")


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """终止 pytest 进程树，避免超时后子服务继续占用 stdout 或 executor。"""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            # start_new_session=True 时 pytest 的进程组 ID 即主进程 PID；主进程退出后仍可清理残留子进程。
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        process.kill()


def run_pytest_streaming(
    command: list[str],
    *,
    cwd: str | Path,
    run_dir: Path,
    timeout: int,
) -> subprocess.CompletedProcess:
    """实时转发 pytest 输出到 Jenkins console，并同步保留完整日志文本。"""
    console_path = Path(run_dir) / "console.log"
    console_path.parent.mkdir(parents=True, exist_ok=True)
    output_parts: list[str] = []
    process_env = os.environ.copy()
    process_env["PYTHONUNBUFFERED"] = "1"
    existing_pythonpath = process_env.get("PYTHONPATH", "")
    process_env["PYTHONPATH"] = os.pathsep.join(part for part in [str(API_TEST_ROOT), existing_pythonpath] if part)
    process_group_options = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=process_env,
        **process_group_options,
    )

    def forward_output() -> None:
        assert process.stdout is not None
        with console_path.open("w", encoding="utf-8") as console_file:
            try:
                for line in iter(process.stdout.readline, ""):
                    safe_line = redact_sensitive_text(line)
                    output_parts.append(safe_line)
                    sys.stdout.write(safe_line)
                    sys.stdout.flush()
                    console_file.write(safe_line)
                    console_file.flush()
            except (OSError, ValueError):
                return

    reader = threading.Thread(target=forward_output, name="pytest-console-forwarder", daemon=True)
    reader.start()
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
        reader.join(timeout=5)
        raise subprocess.TimeoutExpired(
            command,
            timeout=exc.timeout,
            output="".join(output_parts),
            stderr="",
        ) from exc
    reader.join(timeout=5)
    if reader.is_alive():
        _terminate_process_tree(process)
        if process.stdout is not None:
            process.stdout.close()
        reader.join(timeout=5)
    return subprocess.CompletedProcess(command, return_code, stdout="".join(output_parts), stderr="")


def load_case_results(output_path: Path) -> list[dict]:
    """读取 pytest reporter 产物；缺失或损坏时返回空列表供后端安全降级。"""
    try:
        payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return payload if isinstance(payload, list) else []


def merge_case_result_counts(case_results: list[dict], parsed_counts: dict[str, int | float]) -> dict[str, int | float]:
    """以最终 node id 明细为权威计数，避免 teardown error 被 pytest 汇总重复计算。"""
    if not case_results:
        return parsed_counts
    statuses = [item.get("execution_status") for item in case_results]
    return {
        "total_count": len(case_results),
        "failed_count": sum(status in {"failed", "error"} for status in statuses),
        "error_count": statuses.count("error"),
        "passed_count": statuses.count("passed"),
        "skipped_count": statuses.count("skipped"),
        "duration_seconds": parsed_counts.get("duration_seconds", 0.0),
    }


def _decode_timeout_output(value: str | bytes | None) -> str:
    """将 TimeoutExpired 中可能的 bytes 输出统一转成文本，便于写入诊断日志。"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _write_timeout_console_log(run_dir: Path, exc: subprocess.TimeoutExpired) -> None:
    """pytest 超时时仍保留已捕获输出和明确诊断，避免 Jenkins 只有卡死现场。"""
    stdout = redact_sensitive_text(_decode_timeout_output(exc.output))
    stderr = redact_sensitive_text(_decode_timeout_output(exc.stderr))
    timeout_message = f"pytest execution timed out after {exc.timeout} seconds."
    content = "\n".join(part for part in [stdout, stderr, timeout_message] if part)
    (Path(run_dir) / "console.log").write_text(content + "\n", encoding="utf-8")


def _append_console_log(run_dir: Path, message: str) -> None:
    """向 runtime console.log 追加非 pytest 阶段诊断，供 Jenkins artifact 和平台同步查看。"""
    console_path = Path(run_dir) / "console.log"
    with console_path.open("a", encoding="utf-8") as file:
        file.write(("\n" if console_path.stat().st_size else "") + redact_sensitive_text(message).rstrip() + "\n")


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
    try:
        result = subprocess.run(
            command,
            cwd=str(request.api_test_root),
            check=False,
            capture_output=True,
            text=True,
            timeout=request.allure_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        message = f"Allure HTML report generation timed out after {exc.timeout} seconds."
        _append_console_log(request.run_dir, message)
        return {
            "status": "failed",
            "message": message,
        }
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
    cleanup_old_ci_runs(
        api_test_root=request.api_test_root,
        current_run_dir=request.run_dir,
        retention_days=request.retention_days,
    )

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

    command = build_pytest_command(
        targets=targets,
        allure_results_dir=allure_results_dir,
        clean=request.clean,
        retry_count=request.retry_count,
        python_executable=python_executable or sys.executable,
        base_url=request.base_url,
    )
    try:
        result = run_pytest_streaming(
            command,
            cwd=str(request.api_test_root),
            run_dir=request.run_dir,
            timeout=request.pytest_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        _write_timeout_console_log(request.run_dir, exc)
        write_nodeids([], request.run_dir / "failed_nodeids.json")
        return write_summary(
            run_dir=request.run_dir,
            return_code=124,
            failed_nodeids=[],
            allure_results_dir=allure_results_dir,
            allure_report_dir=allure_report_dir,
            allure_report_status="skipped",
            allure_report_message=f"pytest execution timed out after {exc.timeout} seconds; Allure HTML report was not generated.",
            count_fields={
                "total_count": 0,
                "failed_count": 0,
                "passed_count": 0,
                "skipped_count": 0,
                "duration_seconds": 0.0,
            },
        )
    _write_console_log(request.run_dir, result)
    parsed_counts = parse_pytest_summary_counts("\n".join(part for part in [result.stdout or "", result.stderr or ""] if part))
    allure_report = _generate_allure_report(request)

    case_results = load_case_results(request.run_dir / "case_results.json")
    count_fields = merge_case_result_counts(case_results, parsed_counts)
    failed_nodeids = normalize_nodeids(
        case_result.get("node_id", "")
        for case_result in case_results
        if case_result.get("execution_status") in {"failed", "error"}
    )
    write_nodeids(failed_nodeids, request.run_dir / "failed_nodeids.json")
    return write_summary(
        run_dir=request.run_dir,
        return_code=result.returncode,
        failed_nodeids=failed_nodeids,
        allure_results_dir=allure_results_dir,
        allure_report_dir=allure_report_dir,
        allure_report_status=allure_report["status"],
        allure_report_message=allure_report["message"],
        count_fields=count_fields,
        case_results=case_results,
    )


def build_run_dir(api_test_root: Path, run_id: str | None = None) -> Path:
    """构建 CI 运行目录路径（runtime/ci-runs/{run_id}）。"""
    actual_run_id = str(run_id).strip() if run_id is not None else datetime.now().strftime("%Y%m%d_%H%M%S")
    if not RUN_ID_PATTERN.fullmatch(actual_run_id):
        raise ValueError("run_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
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
    parser.add_argument("--base-url", default=None, help="override config.base_url for this CI run")
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
        run_ci_tests(request)
        # Jenkins 负责调度和归档，pytest 用例失败属于测试结果而不是基础设施失败。
        # 失败状态、原始 pytest 返回码和 failed node id 已写入 summary.json / Allure，
        # 因此这里返回 0，避免把包含失败用例的有效测试报告误标记为整条 Jenkins 构建失败。
        return 0

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
        base_url=_normalize_optional_base_url(args.base_url),
    )
    summary = run_ci_tests(request)
    return int(summary["return_code"])


if __name__ == "__main__":
    raise SystemExit(main())
