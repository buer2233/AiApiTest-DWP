"""平台环境 stage 的统一 Python CLI 装配入口。"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Callable, Sequence

from .adapters import SubprocessCommandRunner, UrllibHttpClient
from .configuration import ConfigError, DotEnvConfig
from .dependencies import DependencyAssuranceService
from .deploy import DeployService
from .evidence import EvidenceStore
from .health import HealthService
from .jenkins_api import JenkinsApiClient, JenkinsTriggerConfig, TriggerOutcome
from .models import Diagnostic, RunContext
from .preflight import PreflightService
from .security import Redactor
from .summary import SummaryService
from .testing import TestService


COMMANDS = (
    "preflight",
    "assure-dependencies",
    "deploy",
    "health",
    "test",
    "summary",
    "trigger",
)


def parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("boolean value must be true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AiApiTest-DWP platform bootstrap stage runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        command_parser = subparsers.add_parser(command)
        if command == "trigger":
            command_parser.add_argument("--build-all", choices=("true", "false"), required=True)
            command_parser.add_argument("--run-full-tests", choices=("true", "false"), required=True)
    return parser


def _context_from_environment() -> RunContext:
    workspace = Path(os.environ.get("PLATFORM_BOOTSTRAP_WORKSPACE", Path.cwd()))
    build_id = os.environ.get("PLATFORM_BOOTSTRAP_BUILD_ID", "manual")
    evidence_dir = Path(
        os.environ.get(
            "PLATFORM_BOOTSTRAP_EVIDENCE_DIR",
            workspace / "runtime" / "platform-bootstrap" / build_id,
        )
    )
    return RunContext.create(
        workspace=workspace,
        evidence_dir=evidence_dir,
        build_id=build_id,
        build_url=os.environ.get("PLATFORM_BOOTSTRAP_BUILD_URL", ""),
        build_all=parse_bool(os.environ.get("PLATFORM_BOOTSTRAP_BUILD_ALL", "true")),
        run_full_tests=parse_bool(os.environ.get("PLATFORM_BOOTSTRAP_RUN_FULL_TESTS", "false")),
        source_revision=os.environ.get("PLATFORM_BOOTSTRAP_SOURCE_REVISION", "unknown"),
    )


def run_stage(command: str, options=None) -> int:
    if command == "trigger":
        workspace = Path(os.environ.get("PLATFORM_BOOTSTRAP_WORKSPACE", Path.cwd())).resolve()
        try:
            config = JenkinsTriggerConfig.load(workspace / ".env")
            client = JenkinsApiClient(
                config,
                UrllibHttpClient(),
                monotonic=time.monotonic,
                sleep=time.sleep,
            )
        except ConfigError as exc:
            invocation_dir = (
                workspace
                / "runtime"
                / "platform-bootstrap"
                / f"helper-{os.getpid()}-{time.time_ns()}"
            )
            config_evidence: tuple[str, ...] = ()
            persistence_status = "available"
            try:
                resolved_invocation = invocation_dir.resolve()
                if (
                    resolved_invocation != workspace
                    and workspace not in resolved_invocation.parents
                ):
                    raise ValueError("helper evidence root escapes workspace")
                evidence_path = EvidenceStore(resolved_invocation).write_text(
                    "trigger-configuration.log",
                    f"stage=trigger\nconfig_file=.env\nstatus=invalid\nreason={exc}",
                )
                if evidence_path.is_file():
                    config_evidence = (str(evidence_path),)
                else:
                    persistence_status = "unavailable"
            except (OSError, ValueError):
                persistence_status = "unavailable"
            outcome = TriggerOutcome(
                success=False,
                status="CONFIGURATION_ERROR",
                build_url="",
                queue_url="",
                summary={},
                diagnostics=(
                    Diagnostic(
                        stage="trigger",
                        code="CONFIG_REQUIRED_ENV_MISSING",
                        target=".env",
                        reason="Jenkins trigger configuration is missing or invalid",
                        observed=f"{exc}; evidence_persistence={persistence_status}",
                        evidence=config_evidence,
                        suggestion="Create/fix the private root .env Jenkins URL, Job, username, token, and timeout keys.",
                        rerun="Run trigger-platform-bootstrap again with the same two boolean values.",
                    ),
                ),
            )
            print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2))
            return 1
        outcome = client.trigger(
            build_all=parse_bool(options.build_all),
            run_full_tests=parse_bool(options.run_full_tests),
        )
        print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2))
        return 0 if outcome.success else 1

    context = _context_from_environment()
    try:
        config = DotEnvConfig.load(context.env_file)
        values = config.values
    except ConfigError:
        values = {}
    redactor = Redactor.from_env(values)
    evidence = EvidenceStore(context.evidence_dir, redactor)
    runner = SubprocessCommandRunner(redactor=redactor)

    if command == "preflight":
        result = PreflightService(runner, evidence).run(context)
    elif command == "assure-dependencies":
        result = DependencyAssuranceService(runner, evidence).run(context)
    elif command == "deploy":
        result = DeployService(runner, evidence).run(context)
    elif command == "health":
        result = HealthService(runner, UrllibHttpClient(), evidence).run(context, values)
    elif command == "test":
        result = TestService(runner, UrllibHttpClient(), evidence).run(context, values)
    elif command == "summary":
        result = SummaryService(evidence).run(context, values)
    else:  # pragma: no cover - argparse already prevents this branch.
        raise ValueError(f"unsupported command: {command}")
    return 0 if result.success else 1


def main(
    argv: Sequence[str] | None = None,
    *,
    dispatcher: Callable[[str, object], int] = run_stage,
) -> int:
    arguments = build_parser().parse_args(argv)
    return int(dispatcher(arguments.command, arguments))
