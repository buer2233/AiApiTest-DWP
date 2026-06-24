"""接口自动化执行器适配模块。
本模块是 DRF 后端调用 `api-test/tools/ci_runner.py` 的唯一入口。
后端只传递执行参数并读取 summary，不复制 pytest 命令拼接、失败重试和 Allure 产物生成逻辑。
"""

import json
import subprocess
import sys
from pathlib import Path

from django.conf import settings


class ApiTestRunner:
    """后端到 api-test 执行器的适配器。
    该类负责生成 run_id、调用统一 CI runner，并把执行摘要转换成后端可保存的字典。
    """

    @classmethod
    def run(cls, *, case_path, node_ids=None, retry_mode="none", retry_count=0):
        """执行接口自动化测试任务。
        Args:
            case_path: pytest 模块路径或用例根目录。
            node_ids: 需要精确执行的 pytest node id 列表。
            retry_mode: CI runner 支持的重试模式。
            retry_count: pytest rerun 次数。
        Returns:
            dict: 标准化后的执行摘要，包含 run_id、状态、失败 node id 和产物路径。
        """
        api_test_root = cls.api_test_root()
        run_id = cls.next_run_id()

        # 所有 pytest 执行参数都透传给 api-test 的统一 runner，避免后端重复实现执行规则。
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

        # 后端不因 pytest 返回非 0 直接抛异常，真实执行状态由 summary.json 决定。
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
            # runner 未能写出 summary 时仍返回可登记的错误摘要，便于前端看到失败状态。
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
        """获取 api-test 工程根目录。
        Returns:
            Path: 配置中的 API_TEST_ROOT，未配置时回退到仓库根目录下的 api-test。
        """
        configured_root = getattr(settings, "API_TEST_ROOT", None)
        if configured_root:
            return Path(configured_root)
        return Path(settings.BASE_DIR).parent / "api-test"

    @staticmethod
    def next_run_id() -> str:
        """生成后端触发的测试任务运行 ID。
        Returns:
            str: 带 backend 前缀和微秒时间戳的唯一运行 ID。
        """
        from django.utils import timezone

        return timezone.now().strftime("backend-%Y%m%d-%H%M%S-%f")
