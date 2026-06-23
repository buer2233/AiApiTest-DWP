import json
import subprocess
import sys
from pathlib import Path

from django.conf import settings


class ApiTestRunner:
    @classmethod
    def run(cls, *, case_path, node_ids=None, retry_mode="none", retry_count=0):
        api_test_root = cls.api_test_root()
        run_id = cls.next_run_id()
        command = [
            sys.executable,
            "-m",
            "tools.ci_runner",
            "--case-path",
            case_path,
            "--retry-mode",
            retry_mode,
            "--retry-count",
            str(retry_count),
            "--run-id",
            run_id,
        ]
        for node_id in node_ids or []:
            command.extend(["--node-id", node_id])

        subprocess.run(
            command,
            cwd=str(api_test_root),
            check=False,
            capture_output=True,
            text=True,
        )

        summary_path = api_test_root / "runtime" / "ci-runs" / run_id / "summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        else:
            summary = {
                "status": "error",
                "return_code": 1,
                "failed_nodeids": [],
                "allure_results_dir": str(api_test_root / "runtime" / "ci-runs" / run_id / "allure-results"),
                "allure_report_dir": str(api_test_root / "runtime" / "ci-runs" / run_id / "allure-report"),
            }
        return {
            "run_id": run_id,
            "case_path": case_path,
            "node_ids": list(node_ids or []),
            "retry_mode": retry_mode,
            "retry_count": retry_count,
            "status": summary.get("status", "error"),
            "return_code": summary.get("return_code", 1),
            "failed_nodeids": summary.get("failed_nodeids", []),
            "allure_results_dir": summary.get("allure_results_dir", ""),
            "allure_report_dir": summary.get("allure_report_dir", ""),
            "console_log_path": str(api_test_root / "runtime" / "ci-runs" / run_id / "console.log"),
        }

    @staticmethod
    def api_test_root() -> Path:
        configured_root = getattr(settings, "API_TEST_ROOT", None)
        if configured_root:
            return Path(configured_root)
        return Path(settings.BASE_DIR).parent / "api-test"

    @staticmethod
    def next_run_id() -> str:
        from django.utils import timezone

        return timezone.now().strftime("backend-%Y%m%d-%H%M%S-%f")
