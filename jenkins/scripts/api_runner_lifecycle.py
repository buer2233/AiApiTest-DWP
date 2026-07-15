"""业务 Jenkins Job 的 api-runner 镜像门禁与容器生命周期。"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from platform_bootstrap.dependencies import (
    DependencyDomainSpec,
    compute_domain_hashes,
    default_domain_specs,
)
from platform_bootstrap.security import Redactor


API_RUNNER_IMAGE = "aiapitest-api-runner:local"
API_RUNNER_WORKDIR = "/workspace/AiApiTest-DWP/api-test"
API_RUNNER_COMPONENT = "api-runner"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

LABEL_KEYS = {
    "component": "aiapitest.component",
    "dependency_hash": "aiapitest.dependency-hash",
    "build_input_hash": "aiapitest.build-input-hash",
    "source_revision": "aiapitest.source-revision",
}
REQUIRED_ARTIFACTS = (
    "summary.json",
    "failed_nodeids.json",
    "console.log",
    "allure-results",
    "allure-report",
)
SUMMARY_FIELDS = {
    "status",
    "return_code",
    "failed_nodeids",
    "allure_report_status",
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ImageFingerprint:
    component: str
    dependency_hash: str
    build_input_hash: str
    source_revision: str


@dataclass(frozen=True)
class LifecycleContext:
    workspace: Path
    run_id: str
    job_name: str
    build_id: str
    source_revision: str
    runner_environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class LifecycleResult:
    success: bool
    code: str
    message: str
    container_name: str
    container_id: str
    container_retained: bool
    evidence_dir: Path
    run_dir: Path
    summary: Mapping[str, object] = field(default_factory=dict)


class CommandRunner(Protocol):
    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> CommandResult: ...


class FingerprintProvider(Protocol):
    def current(self, workspace: Path) -> ImageFingerprint: ...


class SubprocessCommandRunner:
    """以 argv 和 ``shell=False`` 调用 Docker CLI，并在返回前脱敏。"""

    def __init__(
        self,
        *,
        run_factory: Callable[..., object] = subprocess.run,
        redactor: Redactor | None = None,
    ):
        self._run_factory = run_factory
        self._redactor = redactor or Redactor()

    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        try:
            completed = self._run_factory(
                list(argv),
                cwd=str(cwd.resolve()),
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                124,
                self._redactor.text(exc.stdout or ""),
                self._redactor.text(exc.stderr or f"command timed out after {timeout_seconds}s"),
            )
        except OSError as exc:
            return CommandResult(127, "", self._redactor.text(exc))
        return CommandResult(
            int(completed.returncode),
            self._redactor.text(completed.stdout or ""),
            self._redactor.text(completed.stderr or ""),
        )


class Task3FingerprintProvider:
    """复用 Task 3 已批准的 api-runner domain/hash API。"""

    def __init__(self, source_revision: str):
        self._source_revision = source_revision

    def current(self, workspace: Path) -> ImageFingerprint:
        domains: Sequence[DependencyDomainSpec] = default_domain_specs(workspace)
        domain = next((item for item in domains if item.name == "api-runner"), None)
        if domain is None:
            raise ValueError("Task 3 api-runner domain is unavailable")
        dependency_hash, build_input_hash = compute_domain_hashes(domain)
        return ImageFingerprint(
            API_RUNNER_COMPONENT,
            dependency_hash,
            build_input_hash,
            self._source_revision,
        )


def _slug(value: str, fallback: str, limit: int) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower().encode("ascii", "ignore").decode("ascii"))
    return normalized.strip("-")[:limit].strip("-") or fallback


def build_runner_name(job_name: str, build_id: str, run_id: str) -> str:
    """构造可追踪、Docker 安全且不会因截断发生碰撞的 runner 名称。"""
    raw = f"{job_name}\0{build_id}\0{run_id}"
    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    job_slug = _slug(job_name, "job", 30)
    build_slug = _slug(build_id, "build", 24)
    run_slug = _slug(run_id, "run", 30)
    return f"aiapitest-api-runner-{job_slug}-{build_slug}-{run_slug}-{suffix}"[:128].rstrip("-")


class ApiRunnerLifecycle:
    def __init__(self, command_runner: CommandRunner, fingerprint_provider: FingerprintProvider):
        self._commands = command_runner
        self._fingerprints = fingerprint_provider

    def execute(self, context: LifecycleContext) -> LifecycleResult:
        workspace = Path(context.workspace).resolve()
        run_dir = workspace / "api-test" / "runtime" / "ci-runs" / context.run_id
        evidence_dir = workspace / "api-test" / "runtime" / "runner-lifecycle" / context.run_id
        if not RUN_ID_PATTERN.fullmatch(context.run_id):
            return LifecycleResult(
                False,
                "RUNNER_LIFECYCLE_FAILED",
                "RUN_ID 必须使用 1-128 位字母、数字、点、下划线或连字符。",
                "",
                "",
                False,
                evidence_dir,
                run_dir,
            )

        redactor = Redactor.from_env(dict(context.runner_environment))
        try:
            evidence_dir = self._safe_path(workspace, evidence_dir)
            run_dir = self._safe_path(workspace, run_dir)
            evidence_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError) as exc:
            return LifecycleResult(
                False,
                "RUNNER_LIFECYCLE_FAILED",
                redactor.text(f"无法创建 runner 证据目录: {exc}"),
                "",
                "",
                False,
                evidence_dir,
                run_dir,
            )

        try:
            expected = self._fingerprints.current(workspace)
        except Exception as exc:  # 指纹计算失败属于镜像前置门禁失败。
            return self._finish(
                False,
                "API_RUNNER_IMAGE_NOT_READY",
                f"api-runner 当前仓库指纹计算失败: {exc}；请先运行平台环境 Job。",
                evidence_dir,
                run_dir,
                redactor=redactor,
            )

        inspect = self._commands.run(
            (
                "docker",
                "image",
                "inspect",
                "--format",
                "{{json .Config.Labels}}",
                API_RUNNER_IMAGE,
            ),
            cwd=workspace,
            timeout_seconds=30,
        )
        labels, gate_error = self._validate_labels(inspect, expected)
        self._write_json(
            evidence_dir / "image-gate.json",
            {
                "image": API_RUNNER_IMAGE,
                "success": gate_error is None,
                "expected": expected.__dict__,
                "actual": labels,
                "inspect_returncode": inspect.returncode,
                "diagnostic": redactor.text(gate_error or "ready"),
            },
        )
        if gate_error:
            return self._finish(
                False,
                "API_RUNNER_IMAGE_NOT_READY",
                f"{gate_error}；请先运行平台环境 Job。",
                evidence_dir,
                run_dir,
                redactor=redactor,
            )

        try:
            rechecked = self._fingerprints.current(workspace)
        except Exception as exc:
            return self._finish(
                False,
                "API_RUNNER_IMAGE_NOT_READY",
                f"创建 runner 前指纹复核失败: {exc}；请先运行平台环境 Job。",
                evidence_dir,
                run_dir,
                redactor=redactor,
            )
        if rechecked != expected:
            return self._finish(
                False,
                "API_RUNNER_IMAGE_NOT_READY",
                "创建 runner 前仓库输入已变化；请重新运行平台环境 Job。",
                evidence_dir,
                run_dir,
                redactor=redactor,
            )

        container_name = build_runner_name(context.job_name, context.build_id, context.run_id)
        create_argv = [
            "docker",
            "create",
            "--name",
            container_name,
            "--workdir",
            API_RUNNER_WORKDIR,
        ]
        for key, value in context.runner_environment:
            create_argv.extend(("--env", f"{key}={value}"))
        create_argv.extend(
            (
                API_RUNNER_IMAGE,
                "python",
                "-m",
                "tools.ci_runner",
                "--from-jenkins-env",
            )
        )

        create = self._commands.run(tuple(create_argv), cwd=workspace, timeout_seconds=60)
        if create.returncode != 0:
            self._write_text(evidence_dir / "create-error.log", redactor.text(create.stderr))
            return self._finish(
                False,
                "RUNNER_LIFECYCLE_FAILED",
                f"runner 创建失败: {create.stderr or create.stdout}",
                evidence_dir,
                run_dir,
                container_name=container_name,
                redactor=redactor,
            )

        container_id = create.stdout.strip() or container_name
        infrastructure_errors: list[str] = []
        start = self._commands.run(
            ("docker", "start", container_name),
            cwd=workspace,
            timeout_seconds=60,
        )
        if start.returncode != 0:
            infrastructure_errors.append(f"docker start 失败: {start.stderr or start.stdout}")
        else:
            wait = self._commands.run(
                ("docker", "wait", container_name),
                cwd=workspace,
                timeout_seconds=60 * 60,
            )
            if wait.returncode != 0:
                infrastructure_errors.append(f"docker wait 失败: {wait.stderr or wait.stdout}")
            else:
                container_exit = self._parse_wait_status(wait.stdout)
                if container_exit is None:
                    infrastructure_errors.append("docker wait 未返回唯一整数退出状态")
                elif container_exit != 0:
                    infrastructure_errors.append(f"runner 容器异常退出: {container_exit}")

        logs = self._commands.run(
            ("docker", "logs", container_name),
            cwd=workspace,
            timeout_seconds=60,
        )
        self._write_text(evidence_dir / "container.log", redactor.text(logs.stdout or logs.stderr))
        if logs.returncode != 0:
            infrastructure_errors.append(f"docker logs 失败: {logs.stderr or logs.stdout}")

        export_error, summary = self._export_artifacts(
            workspace,
            context.run_id,
            container_name,
            evidence_dir,
            run_dir,
            redactor,
        )
        if export_error:
            return self._finish(
                False,
                "RUNNER_ARTIFACT_EXPORT_FAILED",
                export_error,
                evidence_dir,
                run_dir,
                container_name=container_name,
                container_id=container_id,
                container_retained=True,
                summary=summary,
                redactor=redactor,
            )

        cleanup = self._commands.run(
            ("docker", "rm", container_name),
            cwd=workspace,
            timeout_seconds=60,
        )
        if cleanup.returncode != 0:
            infrastructure_errors.append(f"runner 清理失败: {cleanup.stderr or cleanup.stdout}")
            return self._finish(
                False,
                "RUNNER_LIFECYCLE_FAILED",
                "; ".join(infrastructure_errors),
                evidence_dir,
                run_dir,
                container_name=container_name,
                container_id=container_id,
                container_retained=True,
                summary=summary,
                redactor=redactor,
            )

        if summary.get("allure_report_status") != "generated":
            infrastructure_errors.append(
                "Allure HTML report was not generated: "
                + str(summary.get("allure_report_message", ""))
            )
        if infrastructure_errors:
            return self._finish(
                False,
                "RUNNER_LIFECYCLE_FAILED",
                "; ".join(infrastructure_errors),
                evidence_dir,
                run_dir,
                container_name=container_name,
                container_id=container_id,
                summary=summary,
                redactor=redactor,
            )
        return self._finish(
            True,
            "OK",
            "api-runner 生命周期与产物导出完成。",
            evidence_dir,
            run_dir,
            container_name=container_name,
            container_id=container_id,
            summary=summary,
            redactor=redactor,
        )

    @staticmethod
    def _safe_path(workspace: Path, path: Path) -> Path:
        resolved = path.resolve(strict=False)
        if resolved != workspace and workspace not in resolved.parents:
            raise ValueError(f"path escapes workspace: {path}")
        return resolved

    @staticmethod
    def _parse_wait_status(stdout: str) -> int | None:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if len(lines) != 1 or not re.fullmatch(r"\d+", lines[0]):
            return None
        return int(lines[0])

    @staticmethod
    def _validate_labels(
        inspect: CommandResult,
        expected: ImageFingerprint,
    ) -> tuple[dict[str, str], str | None]:
        if inspect.returncode != 0:
            return {}, f"镜像 {API_RUNNER_IMAGE} 不存在或不可检查: {inspect.stderr or inspect.stdout}"
        try:
            value = json.loads(inspect.stdout)
        except json.JSONDecodeError as exc:
            return {}, f"镜像 label 不是合法 JSON: {exc}"
        if not isinstance(value, dict):
            return {}, "镜像 label 缺失"
        labels = {str(key): str(item) for key, item in value.items()}
        for field_name, label_name in LABEL_KEYS.items():
            actual = labels.get(label_name, "")
            wanted = str(getattr(expected, field_name))
            source_unknown_match = (
                field_name == "source_revision"
                and actual == "unknown"
                and wanted == "unknown"
            )
            if not actual or actual != wanted or (actual == "unknown" and not source_unknown_match):
                return labels, f"镜像 label 不匹配: {label_name} expected={wanted} actual={actual or '<missing>'}"
        return labels, None

    def _export_artifacts(
        self,
        workspace: Path,
        run_id: str,
        container_name: str,
        evidence_dir: Path,
        run_dir: Path,
        redactor: Redactor,
    ) -> tuple[str | None, dict[str, object]]:
        staging = evidence_dir / "export-staging"
        partial = evidence_dir / "export-partial"
        errors: list[str] = []
        summary: dict[str, object] = {}
        container_run_dir = f"{API_RUNNER_WORKDIR}/runtime/ci-runs/{run_id}"
        run_dir_owned = False
        try:
            if staging.exists() or partial.exists():
                errors.append("runner 导出 staging 已存在，拒绝覆盖历史失败证据")
            else:
                staging.mkdir(parents=True)
                for artifact in REQUIRED_ARTIFACTS:
                    target = staging / artifact
                    relative_target = target.relative_to(workspace).as_posix()
                    result = self._commands.run(
                        (
                            "docker",
                            "cp",
                            f"{container_name}:{container_run_dir}/{artifact}",
                            relative_target,
                        ),
                        cwd=workspace,
                        timeout_seconds=120,
                    )
                    if result.returncode != 0:
                        errors.append(
                            f"{artifact}: {result.stderr or result.stdout or 'docker cp failed'}"
                        )

            if not errors:
                errors.extend(self._validate_staging(staging))
            if not errors and (run_dir.exists() or run_dir.is_symlink()):
                errors.append(
                    f"标准运行目录已存在，拒绝覆盖: {run_dir.relative_to(workspace).as_posix()}"
                )
            if errors:
                return self._controlled_export_failure(
                    errors,
                    staging,
                    partial,
                    run_dir,
                    run_dir_owned,
                    container_name,
                    container_run_dir,
                    evidence_dir,
                    redactor,
                )

            run_dir.parent.mkdir(parents=True, exist_ok=True)
            staging.replace(run_dir)
            run_dir_owned = True
            summary_value = json.loads(
                (run_dir / "summary.json").read_text(encoding="utf-8")
            )
            if not isinstance(summary_value, dict) or not SUMMARY_FIELDS.issubset(summary_value):
                raise ValueError("final summary.json 缺少冻结字段")
            summary = summary_value
            return None, summary
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            errors.append(f"产物 staging/finalization 异常: {exc}")
            return self._controlled_export_failure(
                errors,
                staging,
                partial,
                run_dir,
                run_dir_owned,
                container_name,
                container_run_dir,
                evidence_dir,
                redactor,
            )

    def _controlled_export_failure(
        self,
        errors: list[str],
        staging: Path,
        partial: Path,
        run_dir: Path,
        run_dir_owned: bool,
        container_name: str,
        container_run_dir: str,
        evidence_dir: Path,
        redactor: Redactor,
    ) -> tuple[str, dict[str, object]]:
        quarantine_source = run_dir if run_dir_owned else staging
        try:
            if (
                (quarantine_source.exists() or quarantine_source.is_symlink())
                and not partial.exists()
                and not partial.is_symlink()
            ):
                quarantine_source.replace(partial)
        except OSError as exc:
            errors.append(f"失败产物隔离异常: {exc}")

        manual = "\n".join(
            f"docker cp {container_name}:{container_run_dir}/{artifact} <workspace-relative-target>"
            for artifact in REQUIRED_ARTIFACTS
        )
        safe_diagnostic = redactor.text(
            f"runner={container_name}\n导出失败项:\n- "
            + "\n- ".join(errors)
            + "\n人工导出指引:\n"
            + manual
        )
        try:
            self._write_text(evidence_dir / "manual-export.txt", safe_diagnostic)
        except OSError as exc:
            errors.append(f"人工导出 evidence 写入异常: {exc}")
        message = redactor.text(
            "产物导出失败，runner 已保留: "
            + "; ".join(errors)
            + f"；人工导出指引: docker cp {container_name}:{container_run_dir}/<artifact> <workspace-relative-target>"
        )
        return message, {}

    @staticmethod
    def _validate_staging(staging: Path) -> list[str]:
        errors: list[str] = []
        for name in REQUIRED_ARTIFACTS:
            path = staging / name
            if not path.exists() and not path.is_symlink():
                errors.append(f"{name} 缺失")
                continue
            if path.is_symlink():
                errors.append(f"{name} 不得为符号链接")
                continue
            if name in {"allure-results", "allure-report"}:
                if not path.is_dir():
                    errors.append(f"{name} 必须为目录")
                else:
                    for child in path.rglob("*"):
                        is_junction = getattr(child, "is_junction", lambda: False)
                        if child.is_symlink() or is_junction():
                            relative = child.relative_to(staging).as_posix()
                            errors.append(f"{relative} 不得为符号链接或 junction")
            elif not path.is_file():
                errors.append(f"{name} 必须为普通文件")

        summary_path = staging / "summary.json"
        if summary_path.is_file() and not summary_path.is_symlink():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"summary.json 非法: {exc}")
            else:
                if not isinstance(summary, dict) or not SUMMARY_FIELDS.issubset(summary):
                    errors.append("summary.json 缺少冻结字段")
                elif not isinstance(summary.get("failed_nodeids"), list):
                    errors.append("summary.json failed_nodeids 必须为数组")

        failed_path = staging / "failed_nodeids.json"
        if failed_path.is_file() and not failed_path.is_symlink():
            try:
                failed = json.loads(failed_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"failed_nodeids.json 非法: {exc}")
            else:
                if not isinstance(failed, list):
                    errors.append("failed_nodeids.json 必须为数组")
        return errors

    def _finish(
        self,
        success: bool,
        code: str,
        message: str,
        evidence_dir: Path,
        run_dir: Path,
        *,
        container_name: str = "",
        container_id: str = "",
        container_retained: bool = False,
        summary: Mapping[str, object] | None = None,
        redactor: Redactor,
    ) -> LifecycleResult:
        safe_message = redactor.text(message)
        result = LifecycleResult(
            success,
            code,
            safe_message,
            container_name,
            container_id,
            container_retained,
            evidence_dir,
            run_dir,
            dict(summary or {}),
        )
        self._write_json(
            evidence_dir / "result.json",
            {
                "success": success,
                "code": code,
                "message": safe_message,
                "container_name": redactor.text(container_name),
                "container_id": redactor.text(container_id),
                "container_retained": container_retained,
                "run_dir": str(run_dir),
                "summary": redactor.mapping(dict(summary or {})),
            },
        )
        return result

    @staticmethod
    def _write_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
