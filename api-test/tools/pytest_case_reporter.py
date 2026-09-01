"""pytest 插件：按最终 node id 输出平台可同步的用例结果。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.sensitive_data import redact_sensitive_text


def pytest_addoption(parser):
    group = parser.getgroup("aiapitest-ci")
    group.addoption(
        "--ci-case-results",
        action="store",
        default="",
        help="将最终 pytest node id 结果写入指定 JSON 文件",
    )


def _case_name(node_id: str) -> str:
    return node_id.rsplit("::", 1)[-1] if "::" in node_id else node_id.rsplit("/", 1)[-1]


def _failure_details(report) -> tuple[str, str]:
    longrepr_text = str(getattr(report, "longreprtext", "") or "").strip()
    if not longrepr_text:
        return "", ""
    error_types = re.findall(r"\b([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception))\b", longrepr_text)
    lines = [line.strip() for line in longrepr_text.splitlines() if line.strip()]
    summary = redact_sensitive_text(lines[-1] if lines else "")[:512]
    return (error_types[-1].rsplit(".", 1)[-1] if error_types else ""), summary


class CaseResultReporter:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.records: dict[str, dict] = {}

    def _record(self, node_id: str, execution_status: str, report) -> None:
        error_type, error_summary = _failure_details(report)
        self.records[node_id] = {
            "node_id": node_id,
            "case_name": _case_name(node_id)[:256],
            "execution_status": execution_status,
            "duration_seconds": round(float(getattr(report, "duration", 0.0) or 0.0), 6),
            "error_type": error_type[:128],
            "error_message_summary": error_summary,
        }

    def pytest_collectreport(self, report):
        if report.failed:
            node_id = str(getattr(report, "nodeid", "") or "collection::<unknown>")
            self._record(node_id, "error", report)
        elif report.skipped:
            node_id = str(getattr(report, "nodeid", "") or "collection::<unknown>")
            self._record(node_id, "skipped", report)

    def pytest_runtest_logreport(self, report):
        # pytest-rerunfailures 的中间报告 outcome=rerun，只保留最后一次结果。
        if report.outcome == "rerun":
            return
        if report.when == "setup":
            if report.failed:
                self._record(report.nodeid, "error", report)
            elif report.skipped:
                self._record(report.nodeid, "skipped", report)
            return
        if report.when == "call":
            if report.passed:
                self._record(report.nodeid, "passed", report)
            elif report.failed:
                self._record(report.nodeid, "failed", report)
            elif report.skipped:
                self._record(report.nodeid, "skipped", report)
            return
        if report.when == "teardown" and report.failed:
            self._record(report.nodeid, "error", report)

    def pytest_sessionfinish(self, session, exitstatus):
        payload = [self.records[node_id] for node_id in sorted(self.records)]
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.output_path.with_suffix(f"{self.output_path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.output_path)


def pytest_configure(config):
    output_value = config.getoption("--ci-case-results")
    if output_value:
        config.pluginmanager.register(CaseResultReporter(Path(output_value)), "aiapitest-case-result-reporter")
