import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tools.pytest_nodeids import load_lastfailed, normalize_nodeids, write_nodeids


API_TEST_ROOT = Path(__file__).resolve().parents[1]
VALID_RETRY_MODES = {"none", "selected", "all-failed", "module"}


@dataclass
class RunRequest:
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
    """Build a pytest command for module runs or exact node id runs."""
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
    """Resolve pytest targets from retry mode and node id inputs."""
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


def ensure_run_dirs(run_dir: Path) -> None:
    """Create the CI run directories used by Jenkins and backend integrations."""
    for path in [
        run_dir,
        run_dir / "allure-results",
        run_dir / "allure-report",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def clear_lastfailed_cache(api_test_root: Path) -> None:
    """Remove stale pytest lastfailed cache before a new run starts."""
    cache_file = Path(api_test_root) / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if cache_file.exists():
        cache_file.unlink()


def write_summary(
    run_dir: Path,
    return_code: int,
    failed_nodeids: list[str],
    allure_results_dir: Path,
    allure_report_dir: Path,
) -> dict:
    """Write and return a compact CI summary."""
    status = "passed" if return_code == 0 else "failed"
    summary = {
        "status": status,
        "return_code": return_code,
        "failed_nodeids": normalize_nodeids(failed_nodeids),
        "allure_results_dir": str(Path(allure_results_dir)),
        "allure_report_dir": str(Path(allure_report_dir)),
    }
    output_path = Path(run_dir) / "summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _write_console_log(run_dir: Path, result: subprocess.CompletedProcess) -> None:
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    content = "\n".join(part for part in [stdout, stderr] if part)
    (Path(run_dir) / "console.log").write_text(content, encoding="utf-8")


def _generate_allure_report(request: RunRequest) -> None:
    allure_executable = shutil.which("allure")
    if not allure_executable:
        return

    command = [
        allure_executable,
        "generate",
        str(Path(request.run_dir) / "allure-results"),
        "-o",
        str(Path(request.run_dir) / "allure-report"),
        "--clean",
    ]
    subprocess.run(command, cwd=str(request.api_test_root), check=False)
    if request.open_report:
        subprocess.run(
            [allure_executable, "open", str(Path(request.run_dir) / "allure-report")],
            cwd=str(request.api_test_root),
            check=False,
        )


def run_ci_tests(request: RunRequest, python_executable: str = "python") -> dict:
    """Run pytest for CI and write console, failed node ids and summary artifacts."""
    request.api_test_root = Path(request.api_test_root)
    request.run_dir = Path(request.run_dir)
    ensure_run_dirs(request.run_dir)

    targets = resolve_pytest_targets(request)
    allure_results_dir = request.run_dir / "allure-results"
    allure_report_dir = request.run_dir / "allure-report"

    if not targets:
        write_nodeids([], request.run_dir / "failed_nodeids.json")
        (request.run_dir / "console.log").write_text("No pytest targets resolved.\n", encoding="utf-8")
        return write_summary(
            run_dir=request.run_dir,
            return_code=0,
            failed_nodeids=[],
            allure_results_dir=allure_results_dir,
            allure_report_dir=allure_report_dir,
        )

    clear_lastfailed_cache(request.api_test_root)
    command = build_pytest_command(
        targets=targets,
        allure_results_dir=allure_results_dir,
        clean=request.clean,
        retry_count=request.retry_count,
        python_executable=python_executable,
    )
    result = subprocess.run(
        command,
        cwd=str(request.api_test_root),
        check=False,
        capture_output=True,
        text=True,
    )
    _write_console_log(request.run_dir, result)
    _generate_allure_report(request)

    failed_nodeids = load_lastfailed(request.api_test_root / ".pytest_cache")
    write_nodeids(failed_nodeids, request.run_dir / "failed_nodeids.json")
    return write_summary(
        run_dir=request.run_dir,
        return_code=result.returncode,
        failed_nodeids=failed_nodeids,
        allure_results_dir=allure_results_dir,
        allure_report_dir=allure_report_dir,
    )


def build_run_dir(api_test_root: Path, run_id: str | None = None) -> Path:
    actual_run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(api_test_root) / "runtime" / "ci-runs" / actual_run_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run api-test pytest cases for CI.")
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
    args = parse_args(argv)
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
