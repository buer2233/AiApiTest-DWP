"""Jenkins controller 上的标准库 api-runner 生命周期入口。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from api_runner_lifecycle import (
    ApiRunnerLifecycle,
    LifecycleContext,
    LifecycleResult,
    SubprocessCommandRunner,
    Task3FingerprintProvider,
)
from platform_bootstrap.security import Redactor


RUNNER_ENVIRONMENT_KEYS = (
    "CASE_PATH",
    "RUN_ID",
    "MODULE_NAME",
    "PYTEST_NODE_IDS",
    "RETRY_MODE",
    "RETRY_COUNT",
    "CLEAN_ALLURE",
    "OPEN_REPORT",
    "CI_RUN_RETENTION_DAYS",
    "CI_RUNNER_ENV",
    # api-test 的目标环境与角色凭据；账号 JSON 由 Jenkins Secret Text 注入。
    "TARGET_BASE_URL",
    "E9_BASE_URL",
    "E9_LOGINID",
    "E9_USERPASSWORD",
    "E9_ACCOUNTS_JSON",
    "E9_EMPLOYEE1_LOGINID",
    "E9_EMPLOYEE1_PASSWORD",
    "E9_EMPLOYEE2_LOGINID",
    "E9_EMPLOYEE2_PASSWORD",
    "E9_EMPLOYEE3_LOGINID",
    "E9_EMPLOYEE3_PASSWORD",
    "E9_EMPLOYEE4_LOGINID",
    "E9_EMPLOYEE4_PASSWORD",
    "E9_EMPLOYEE5_LOGINID",
    "E9_EMPLOYEE5_PASSWORD",
)


def build_context(
    env: Mapping[str, str],
    *,
    cwd: Path,
) -> LifecycleContext:
    # Jenkins `dir(...)` 不保证同步改写 WORKSPACE，实际命令目录才是当前检出仓库。
    workspace = Path(cwd).resolve()
    build_id = env.get("BUILD_TAG") or env.get("BUILD_NUMBER") or "unknown"
    run_id = env.get("RUN_ID") or env.get("BUILD_TAG") or f"jenkins-{env.get('BUILD_NUMBER', 'unknown')}"
    defaults = {
        "CASE_PATH": "",
        "RUN_ID": run_id,
        "MODULE_NAME": "",
        "PYTEST_NODE_IDS": "",
        "RETRY_MODE": "none",
        "RETRY_COUNT": "0",
        "CLEAN_ALLURE": "true",
        "OPEN_REPORT": "false",
        "CI_RUN_RETENTION_DAYS": "30",
        "CI_RUNNER_ENV": "jenkins",
        "TARGET_BASE_URL": "",
        "E9_BASE_URL": "",
        "E9_LOGINID": "",
        "E9_USERPASSWORD": "",
        "E9_ACCOUNTS_JSON": "",
        "E9_EMPLOYEE1_LOGINID": "",
        "E9_EMPLOYEE1_PASSWORD": "",
        "E9_EMPLOYEE2_LOGINID": "",
        "E9_EMPLOYEE2_PASSWORD": "",
        "E9_EMPLOYEE3_LOGINID": "",
        "E9_EMPLOYEE3_PASSWORD": "",
        "E9_EMPLOYEE4_LOGINID": "",
        "E9_EMPLOYEE4_PASSWORD": "",
        "E9_EMPLOYEE5_LOGINID": "",
        "E9_EMPLOYEE5_PASSWORD": "",
    }
    runner_environment = []
    for key in RUNNER_ENVIRONMENT_KEYS:
        value = env.get(key, defaults[key])
        if key == "RUN_ID":
            value = run_id
        elif key == "OPEN_REPORT":
            value = "false"
        elif key == "CI_RUNNER_ENV":
            value = "jenkins"
        runner_environment.append((key, value))

    return LifecycleContext(
        workspace=workspace,
        run_id=run_id,
        job_name=env.get("JOB_NAME", "jenkins-job"),
        build_id=build_id,
        source_revision=env.get("GIT_COMMIT") or "unknown",
        runner_environment=tuple(runner_environment),
    )


def _result_payload(result: LifecycleResult) -> dict[str, object]:
    return {
        "success": result.success,
        "code": result.code,
        "message": result.message,
        "container_name": result.container_name,
        "container_id": result.container_id,
        "container_retained": result.container_retained,
        "evidence_dir": str(result.evidence_dir),
        "run_dir": str(result.run_dir),
        "summary": dict(result.summary),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    lifecycle: object | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Run an isolated api-runner container")
    parser.add_argument("command", choices=("execute",))
    args = parser.parse_args(list(argv) if argv is not None else None)
    current_env = dict(os.environ if env is None else env)
    current_cwd = Path.cwd() if cwd is None else Path(cwd)
    context = build_context(current_env, cwd=current_cwd)
    service = lifecycle or ApiRunnerLifecycle(
        SubprocessCommandRunner(),
        Task3FingerprintProvider(context.source_revision),
    )
    if args.command != "execute":
        return 2
    result = service.execute(context)
    safe_payload = Redactor.from_env(current_env).mapping(_result_payload(result))
    print(json.dumps(safe_payload, ensure_ascii=False, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
