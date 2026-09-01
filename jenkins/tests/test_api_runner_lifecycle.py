"""Stage13 Task 4 api-runner 生命周期与产物回传契约测试。"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import api_runner_cli  # noqa: E402
import api_runner_lifecycle as lifecycle  # noqa: E402
from api_runner_lifecycle import (  # noqa: E402
    API_RUNNER_IMAGE,
    API_RUNNER_WORKDIR,
    ApiRunnerLifecycle,
    CommandResult,
    ImageFingerprint,
    LifecycleContext,
    SubprocessCommandRunner,
    Task3FingerprintProvider,
    build_runner_name,
)


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


def fingerprint(**overrides) -> ImageFingerprint:
    values = {
        "component": "api-runner",
        "dependency_hash": "dep-hash",
        "build_input_hash": "build-hash",
        "source_revision": "commit-123",
    }
    values.update(overrides)
    return ImageFingerprint(**values)


def labels_for(value: ImageFingerprint | None = None) -> dict[str, str]:
    current = value or fingerprint()
    return {
        LABEL_KEYS["component"]: current.component,
        LABEL_KEYS["dependency_hash"]: current.dependency_hash,
        LABEL_KEYS["build_input_hash"]: current.build_input_hash,
        LABEL_KEYS["source_revision"]: current.source_revision,
    }


def write_container_artifacts(
    root: Path,
    *,
    status: str = "passed",
    return_code: int = 0,
    allure_status: str = "generated",
    failed_nodeids: list[str] | None = None,
) -> None:
    failed = list(failed_nodeids or [])
    root.mkdir(parents=True, exist_ok=True)
    (root / "allure-results").mkdir()
    (root / "allure-report").mkdir()
    (root / "console.log").write_text("pytest output\n", encoding="utf-8")
    (root / "failed_nodeids.json").write_text(
        json.dumps(failed, ensure_ascii=False), encoding="utf-8"
    )
    (root / "summary.json").write_text(
        json.dumps(
            {
                "status": status,
                "return_code": return_code,
                "failed_nodeids": failed,
                "allure_report_status": allure_status,
                "allure_report_message": "report status",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class FakeFingerprintProvider:
    def __init__(self, *values: ImageFingerprint):
        self.values = list(values or (fingerprint(),))
        self.calls: list[Path] = []

    def current(self, workspace: Path) -> ImageFingerprint:
        self.calls.append(workspace)
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]


class FakeDockerRunner:
    """模拟 Docker CLI，并把容器产物复制到 helper 指定的相对 host 路径。"""

    def __init__(
        self,
        artifact_root: Path,
        *,
        labels: dict[str, str] | None = None,
        failures: dict[str, CommandResult] | None = None,
        omitted_copies: tuple[str, ...] = (),
        wait_output: str = "0\n",
        logs_output: str = "runner log\n",
    ):
        self.artifact_root = artifact_root
        self.labels = labels_for() if labels is None else labels
        self.failures = dict(failures or {})
        self.omitted_copies = set(omitted_copies)
        self.wait_output = wait_output
        self.logs_output = logs_output
        self.calls: list[tuple[tuple[str, ...], Path, int]] = []

    @staticmethod
    def _step(argv: tuple[str, ...]) -> str:
        if argv[:3] == ("docker", "image", "inspect"):
            return "inspect"
        if argv[:2] == ("docker", "create"):
            return "create"
        if argv[:2] == ("docker", "start"):
            return "start"
        if argv[:2] == ("docker", "wait"):
            return "wait"
        if argv[:2] == ("docker", "logs"):
            return "logs"
        if argv[:2] == ("docker", "cp"):
            return f"cp:{Path(argv[2].split(':', 1)[1]).name}"
        if argv[:2] == ("docker", "rm"):
            return "rm"
        raise AssertionError(f"unexpected argv: {argv}")

    def run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        argv = tuple(argv)
        cwd = Path(cwd)
        self.calls.append((argv, cwd, timeout_seconds))
        step = self._step(argv)
        if step in self.failures:
            return self.failures[step]
        if step == "inspect":
            return CommandResult(0, json.dumps(self.labels), "")
        if step == "create":
            return CommandResult(0, "container-id-123\n", "")
        if step == "start":
            return CommandResult(0, f"{argv[-1]}\n", "")
        if step == "wait":
            return CommandResult(0, self.wait_output, "")
        if step == "logs":
            return CommandResult(0, self.logs_output, "")
        if step.startswith("cp:"):
            name = step.removeprefix("cp:")
            if name not in self.omitted_copies:
                source = self.artifact_root / name
                destination = cwd / Path(argv[3])
                if source.is_dir():
                    shutil.copytree(source, destination, symlinks=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination, follow_symlinks=False)
            return CommandResult(0, "", "")
        if step == "rm":
            return CommandResult(0, "", "")
        raise AssertionError(step)


def make_context(tmp_path: Path, **overrides) -> LifecycleContext:
    values = {
        "workspace": tmp_path,
        "run_id": "run-123",
        "job_name": "Folder/接口测试 Job",
        "build_id": "jenkins-job-42",
        "source_revision": "commit-123",
        "runner_environment": (
            ("CASE_PATH", "test_case/test_gbif_case"),
            ("RUN_ID", "run-123"),
            ("MODULE_NAME", "GBIF"),
            ("PYTEST_NODE_IDS", "test_one\ntest_two,with-comma"),
            ("RETRY_MODE", "none"),
            ("RETRY_COUNT", "0"),
            ("CLEAN_ALLURE", "true"),
            ("OPEN_REPORT", "false"),
            ("CI_RUN_RETENTION_DAYS", "30"),
            ("CI_RUNNER_ENV", "jenkins"),
        ),
    }
    values.update(overrides)
    return LifecycleContext(**values)


def execute_ready(
    tmp_path: Path,
    *,
    runner: FakeDockerRunner | None = None,
    provider: FakeFingerprintProvider | None = None,
    context: LifecycleContext | None = None,
):
    artifacts = tmp_path / "container-artifacts"
    if not artifacts.exists():
        write_container_artifacts(artifacts)
    actual_runner = runner or FakeDockerRunner(artifacts)
    actual_provider = provider or FakeFingerprintProvider()
    actual_context = context or make_context(tmp_path)
    result = ApiRunnerLifecycle(actual_runner, actual_provider).execute(actual_context)
    return result, actual_runner, actual_provider


def command_steps(runner: FakeDockerRunner) -> list[str]:
    return [runner._step(argv) for argv, _cwd, _timeout in runner.calls]


@pytest.mark.parametrize(
    "job_name,build_id,run_id",
    [
        ("中文 空格/Folder/Job", "build 1", "run-1"),
        ("", "", "run-2"),
        ("A" * 300, "B" * 300, "C" * 120),
    ],
)
def test_runner_name_is_traceable_docker_safe_and_bounded(job_name, build_id, run_id):
    name = build_runner_name(job_name, build_id, run_id)

    assert name.startswith("aiapitest-api-runner-")
    assert len(name) <= 128
    assert name == name.lower()
    assert all(character.isascii() and (character.isalnum() or character == "-") for character in name)


def test_runner_name_hash_prevents_truncation_and_build_collisions():
    first = build_runner_name("folder/" + "A" * 200, "build-1", "same-run")
    second = build_runner_name("folder/" + "A" * 200, "build-2", "same-run")
    third = build_runner_name("folder/" + "A" * 199 + "B", "build-1", "same-run")

    assert len({first, second, third}) == 3


@pytest.mark.parametrize("run_id", ["", "../escape", "bad/run", "a" * 129])
def test_invalid_run_id_fails_before_evidence_or_docker_calls(tmp_path, run_id):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts)

    result = ApiRunnerLifecycle(runner, FakeFingerprintProvider()).execute(
        make_context(tmp_path, run_id=run_id)
    )

    assert result.success is False
    assert runner.calls == []
    assert not (tmp_path / "api-test" / "runtime").exists()


def test_cli_context_uses_git_commit_verbatim_and_only_runner_whitelist(tmp_path):
    env = {
        "WORKSPACE": str(tmp_path),
        "JOB_NAME": "Api Test",
        "BUILD_TAG": "jenkins-api-7",
        "GIT_COMMIT": "commit-from-jenkins",
        "RUN_ID": "run-7",
        "CASE_PATH": "test_case/test_gbif_case",
        "MODULE_NAME": "GBIF",
        "PYTEST_NODE_IDS": "one\ntwo,three",
        "RETRY_MODE": "selected",
        "RETRY_COUNT": "1",
        "CLEAN_ALLURE": "false",
        "OPEN_REPORT": "true",
        "CI_RUN_RETENTION_DAYS": "45",
        "CI_RUNNER_ENV": "wrong",
        "TARGET_BASE_URL": "https://registered.example.invalid/e9",
        "E9_BASE_URL": "https://legacy.example.invalid/e9",
        "E9_LOGINID": "admin-placeholder",
        "E9_USERPASSWORD": "password-placeholder",
        "E9_EMPLOYEE1_LOGINID": "employee-one-placeholder",
        "E9_EMPLOYEE1_PASSWORD": "employee-password-placeholder",
        "E9_ACCOUNTS_JSON": '{"admin":{"user_name":"admin-placeholder","password":"password-placeholder"}}',
        "JENKINS_API_TOKEN": "must-not-pass",
        "MYSQL_ROOT_PASSWORD": "must-not-pass",
    }

    context = api_runner_cli.build_context(env, cwd=tmp_path)
    passed = dict(context.runner_environment)

    assert context.source_revision == "commit-from-jenkins"
    assert context.build_id == "jenkins-api-7"
    assert set(passed) == {
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
        "TARGET_BASE_URL",
        "E9_BASE_URL",
        "E9_LOGINID",
        "E9_USERPASSWORD",
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
        "E9_ACCOUNTS_JSON",
    }
    assert passed["OPEN_REPORT"] == "false"
    assert passed["CI_RUNNER_ENV"] == "jenkins"
    assert "must-not-pass" not in repr(context)


def test_cli_context_keeps_target_and_e9_credentials_for_isolated_runner(tmp_path):
    """隔离 runner 必须透传目标地址和账号变量，但不放行无关 Jenkins 密钥。"""
    context = api_runner_cli.build_context(
        {
            "TARGET_BASE_URL": "https://registered.example.invalid/e9",
            "E9_LOGINID": "admin-placeholder",
            "E9_USERPASSWORD": "password-placeholder",
            "E9_EMPLOYEE2_LOGINID": "employee-two-placeholder",
            "E9_EMPLOYEE2_PASSWORD": "employee-two-password-placeholder",
            "JENKINS_API_TOKEN": "must-not-pass",
        },
        cwd=tmp_path,
    )

    passed = dict(context.runner_environment)
    assert passed["TARGET_BASE_URL"] == "https://registered.example.invalid/e9"
    assert passed["E9_LOGINID"] == "admin-placeholder"
    assert passed["E9_EMPLOYEE2_LOGINID"] == "employee-two-placeholder"
    assert "JENKINS_API_TOKEN" not in passed


def test_cli_context_uses_unknown_without_dirty_revision_fallback(tmp_path):
    context = api_runner_cli.build_context(
        {
            "WORKSPACE": str(tmp_path),
            "JOB_NAME": "Api Test",
            "BUILD_NUMBER": "8",
            "RUN_ID": "run-8",
        },
        cwd=tmp_path,
    )

    assert context.source_revision == "unknown"


def test_cli_context_uses_current_checkout_directory_for_local_mounted_jobs(tmp_path):
    current_checkout = tmp_path / "mounted-repository"
    stale_jenkins_workspace = tmp_path / "jenkins-job-workspace"
    current_checkout.mkdir()
    stale_jenkins_workspace.mkdir()

    context = api_runner_cli.build_context(
        {
            "WORKSPACE": str(stale_jenkins_workspace),
            "RUN_ID": "run-local-mounted",
        },
        cwd=current_checkout,
    )

    assert context.workspace == current_checkout.resolve()


def test_task3_fingerprint_provider_selects_only_api_runner_domain(tmp_path, monkeypatch):
    backend = lifecycle.DependencyDomainSpec("backend", "backend", tmp_path, (), (), ())
    api_runner = lifecycle.DependencyDomainSpec("api-runner", "api-runner", tmp_path, (), (), ())
    hashed = []
    monkeypatch.setattr(lifecycle, "default_domain_specs", lambda workspace: (backend, api_runner))
    monkeypatch.setattr(
        lifecycle,
        "compute_domain_hashes",
        lambda domain: hashed.append(domain.name) or ("dep", "build"),
    )

    actual = Task3FingerprintProvider("revision-verbatim").current(tmp_path)

    assert hashed == ["api-runner"]
    assert actual == ImageFingerprint("api-runner", "dep", "build", "revision-verbatim")


def test_missing_image_fails_gate_without_create_build_or_install(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(
        artifacts,
        failures={"inspect": CommandResult(1, "", "No such image")},
    )

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.success is False
    assert result.code == "API_RUNNER_IMAGE_NOT_READY"
    assert command_steps(runner) == ["inspect"]
    assert "先运行平台环境 Job" in result.message


@pytest.mark.parametrize("field", list(LABEL_KEYS))
@pytest.mark.parametrize("mode", ["missing", "unknown", "mismatch"])
def test_each_required_label_is_gated_before_create(tmp_path, field, mode):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    actual_labels = labels_for()
    key = LABEL_KEYS[field]
    if mode == "missing":
        actual_labels.pop(key)
    elif mode == "unknown":
        actual_labels[key] = "unknown"
    else:
        actual_labels[key] = "different"
    runner = FakeDockerRunner(artifacts, labels=actual_labels)

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.success is False
    assert result.code == "API_RUNNER_IMAGE_NOT_READY"
    assert command_steps(runner) == ["inspect"]


def test_source_revision_allows_matching_unknown_for_local_mounted_jobs(tmp_path):
    expected = fingerprint(source_revision="unknown")
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts, labels=labels_for(expected))
    provider = FakeFingerprintProvider(expected)

    result, runner, provider = execute_ready(
        tmp_path,
        runner=runner,
        provider=provider,
        context=make_context(tmp_path, source_revision="unknown"),
    )

    assert result.success is True
    assert result.code == "OK"
    assert len(provider.calls) == 2
    assert "create" in command_steps(runner)


@pytest.mark.parametrize("field", ["component", "dependency_hash", "build_input_hash"])
def test_non_revision_labels_reject_matching_unknown_values(tmp_path, field):
    expected = fingerprint(**{field: "unknown"})
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts, labels=labels_for(expected))

    result, runner, _provider = execute_ready(
        tmp_path,
        runner=runner,
        provider=FakeFingerprintProvider(expected),
    )

    assert result.success is False
    assert result.code == "API_RUNNER_IMAGE_NOT_READY"
    assert command_steps(runner) == ["inspect"]


def test_workspace_fingerprint_change_before_create_fails_without_container(tmp_path):
    changed = fingerprint(build_input_hash="changed")
    provider = FakeFingerprintProvider(fingerprint(), changed)

    result, runner, provider = execute_ready(tmp_path, provider=provider)

    assert result.success is False
    assert result.code == "API_RUNNER_IMAGE_NOT_READY"
    assert command_steps(runner) == ["inspect"]
    assert len(provider.calls) == 2


def test_successful_lifecycle_uses_fixed_image_workdir_command_and_no_mount(tmp_path):
    result, runner, provider = execute_ready(tmp_path)
    steps = command_steps(runner)

    assert result.success is True
    assert result.code == "OK"
    assert len(provider.calls) == 2
    assert steps == [
        "inspect",
        "create",
        "start",
        "wait",
        "logs",
        *[f"cp:{name}" for name in REQUIRED_ARTIFACTS],
        "rm",
    ]
    create_argv = next(argv for argv, _cwd, _timeout in runner.calls if argv[:2] == ("docker", "create"))
    assert create_argv[create_argv.index("--workdir") + 1] == API_RUNNER_WORKDIR
    assert create_argv[-5:] == (
        API_RUNNER_IMAGE,
        "python",
        "-m",
        "tools.ci_runner",
        "--from-jenkins-env",
    )
    assert "--volume" not in create_argv
    assert "-v" not in create_argv
    assert "--mount" not in create_argv
    assert not any("docker.sock" in item or item.endswith(".env") for item in create_argv)


def test_create_passes_exact_env_values_as_argv_without_shell_interpretation(tmp_path):
    context = make_context(tmp_path)
    result, runner, _provider = execute_ready(tmp_path, context=context)
    create_argv = next(argv for argv, _cwd, _timeout in runner.calls if argv[:2] == ("docker", "create"))
    passed_env = [create_argv[index + 1] for index, item in enumerate(create_argv) if item == "--env"]

    assert result.success is True
    assert passed_env == [f"{key}={value}" for key, value in context.runner_environment]
    assert "PYTEST_NODE_IDS=test_one\ntest_two,with-comma" in passed_env


def test_docker_cp_uses_posix_container_sources_and_relative_host_targets(tmp_path):
    result, runner, _provider = execute_ready(tmp_path)

    assert result.success is True
    for argv, cwd, _timeout in runner.calls:
        if argv[:2] != ("docker", "cp"):
            continue
        source, target = argv[2], argv[3]
        assert source.startswith(f"{result.container_name}:{API_RUNNER_WORKDIR}/runtime/ci-runs/run-123/")
        assert "\\" not in source
        assert not Path(target).is_absolute()
        assert ":" not in target
        assert cwd == tmp_path.resolve()


@pytest.mark.parametrize(
    "status,return_code,allure_status,expected_success",
    [
        ("passed", 0, "generated", True),
        ("failed", 1, "generated", True),
        ("passed", 0, "failed", False),
        ("passed", 0, "skipped", False),
    ],
)
def test_summary_is_the_test_fact_and_allure_generation_is_independent(
    tmp_path, status, return_code, allure_status, expected_success
):
    artifacts = tmp_path / "container-artifacts"
    failed = ["test_demo.py::test_failed"] if status == "failed" else []
    write_container_artifacts(
        artifacts,
        status=status,
        return_code=return_code,
        allure_status=allure_status,
        failed_nodeids=failed,
    )

    result, runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts, wait_output="0\n")
    )

    assert result.success is expected_success
    assert result.summary["status"] == status
    assert result.summary["return_code"] == return_code
    assert result.summary["failed_nodeids"] == failed
    assert "rm" in command_steps(runner)


@pytest.mark.parametrize("step", ["create", "start", "wait", "logs"])
def test_each_runner_lifecycle_failure_is_infrastructure_failure(tmp_path, step):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(
        artifacts,
        failures={step: CommandResult(17, "", f"{step} failed")},
    )

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.success is False
    if step == "create":
        assert result.code != "RUNNER_ARTIFACT_EXPORT_FAILED"
        assert "cp:summary.json" not in command_steps(runner)
        assert "rm" not in command_steps(runner)
    else:
        assert (tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123" / "summary.json").is_file()
        assert "rm" in command_steps(runner)


@pytest.mark.parametrize("wait_output", ["", "abc", "0\n1\n"])
def test_invalid_docker_wait_stdout_is_infrastructure_failure_after_export(tmp_path, wait_output):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)

    result, runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts, wait_output=wait_output)
    )

    assert result.success is False
    assert result.summary["status"] == "passed"
    assert "rm" in command_steps(runner)


def test_nonzero_container_exit_is_infrastructure_failure_even_with_passed_summary(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)

    result, runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts, wait_output="23\n")
    )

    assert result.success is False
    assert result.summary["status"] == "passed"
    assert "rm" in command_steps(runner)


@pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
def test_each_docker_cp_failure_keeps_runner_and_never_creates_standard_run(tmp_path, artifact):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(
        artifacts,
        failures={f"cp:{artifact}": CommandResult(9, "", f"copy {artifact} failed")},
    )

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.success is False
    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)
    assert not (tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123").exists()
    assert (Path(result.evidence_dir) / "export-partial").exists()


@pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
def test_cp_success_without_required_item_is_export_failure(tmp_path, artifact):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts, omitted_copies=(artifact,))

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)


@pytest.mark.parametrize("artifact,bad_value", [("summary.json", "{"), ("failed_nodeids.json", "{}")])
def test_invalid_required_json_is_export_failure(tmp_path, artifact, bad_value):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    (artifacts / artifact).write_text(bad_value, encoding="utf-8")

    result, runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts)
    )

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)


def test_required_artifact_symlink_is_rejected_and_runner_is_retained(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    target = artifacts / "real-console.log"
    target.write_text("real\n", encoding="utf-8")
    (artifacts / "console.log").unlink()
    try:
        os.symlink(target, artifacts / "console.log")
    except OSError as exc:
        pytest.skip(f"current filesystem cannot create symlink: {exc.__class__.__name__}")

    result, runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts)
    )

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)


def test_nested_artifact_symlink_is_rejected_without_os_symlink_privileges(
    tmp_path, monkeypatch
):
    staging = tmp_path / "staging"
    write_container_artifacts(staging)
    nested = staging / "allure-results" / "linked-result.json"
    nested.write_text("{}", encoding="utf-8")
    original_is_symlink = Path.is_symlink

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == nested or original_is_symlink(path),
    )

    errors = ApiRunnerLifecycle._validate_staging(staging)

    assert any("allure-results/linked-result.json" in error for error in errors)


def test_existing_final_run_is_not_overwritten_and_runner_is_retained(tmp_path):
    existing = tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123"
    existing.mkdir(parents=True)
    marker = existing / "owner.txt"
    marker.write_text("existing", encoding="utf-8")

    result, runner, _provider = execute_ready(tmp_path)

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert marker.read_text(encoding="utf-8") == "existing"
    assert "rm" not in command_steps(runner)


def assert_controlled_export_failure(result, runner):
    evidence_dir = Path(result.evidence_dir)

    assert result.success is False
    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)
    assert (evidence_dir / "manual-export.txt").is_file()
    assert (evidence_dir / "result.json").is_file()


def test_staging_mkdir_failure_is_controlled_export_failure(tmp_path, monkeypatch):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts)
    staging = (
        tmp_path
        / "api-test"
        / "runtime"
        / "runner-lifecycle"
        / "run-123"
        / "export-staging"
    ).resolve()
    original_mkdir = Path.mkdir

    def fail_staging_mkdir(path, *args, **kwargs):
        if path.resolve(strict=False) == staging:
            raise OSError("token=staging-secret")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_staging_mkdir)

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert_controlled_export_failure(result, runner)
    assert "staging-secret" not in result.message


@pytest.mark.parametrize("target_kind", ["partial", "final"])
def test_atomic_replace_failure_is_controlled_export_failure(
    tmp_path, monkeypatch, target_kind
):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    failures = (
        {"cp:summary.json": CommandResult(7, "", "copy failed")}
        if target_kind == "partial"
        else {}
    )
    runner = FakeDockerRunner(artifacts, failures=failures)
    evidence_dir = (
        tmp_path / "api-test" / "runtime" / "runner-lifecycle" / "run-123"
    ).resolve()
    failed_target = (
        evidence_dir / "export-partial"
        if target_kind == "partial"
        else tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123"
    ).resolve()
    original_replace = Path.replace

    def fail_selected_replace(path, target):
        if Path(target).resolve(strict=False) == failed_target:
            raise OSError(f"token={target_kind}-replace-secret")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_selected_replace)

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert_controlled_export_failure(result, runner)
    assert f"{target_kind}-replace-secret" not in result.message


@pytest.mark.parametrize("mode", ["malformed", "read-error"])
def test_final_summary_failure_is_controlled_and_quarantines_standard_run(
    tmp_path, monkeypatch, mode
):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(artifacts)
    final_run = (
        tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123"
    ).resolve()
    final_summary = final_run / "summary.json"
    original_read_text = Path.read_text

    def fail_final_summary(path, *args, **kwargs):
        if path.resolve(strict=False) == final_summary:
            if mode == "malformed":
                return "{"
            raise OSError("token=summary-read-secret")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_final_summary)

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert_controlled_export_failure(result, runner)
    assert not final_run.exists()
    assert (Path(result.evidence_dir) / "export-partial").is_dir()
    assert "summary-read-secret" not in result.message


def test_export_failure_has_priority_over_nonzero_container_exit(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    runner = FakeDockerRunner(
        artifacts,
        wait_output="21\n",
        failures={"cp:summary.json": CommandResult(8, "", "copy failed")},
    )

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert "rm" not in command_steps(runner)


def test_cleanup_failure_preserves_exported_summary_but_fails_infrastructure(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts, status="failed", return_code=1)
    runner = FakeDockerRunner(
        artifacts,
        failures={"rm": CommandResult(5, "", "remove failed")},
    )

    result, runner, _provider = execute_ready(tmp_path, runner=runner)

    final_summary = tmp_path / "api-test" / "runtime" / "ci-runs" / "run-123" / "summary.json"
    assert result.success is False
    assert result.code != "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert result.container_retained is True
    assert result.summary["status"] == "failed"
    assert json.loads(final_summary.read_text(encoding="utf-8"))["return_code"] == 1


def test_export_failure_diagnostic_is_redacted_and_contains_manual_copy_guidance(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    write_container_artifacts(artifacts)
    secret = "super-secret-value"
    runner = FakeDockerRunner(
        artifacts,
        logs_output=f"token={secret}\n",
        failures={"cp:summary.json": CommandResult(7, "", f"token={secret}")},
    )

    result, _runner, _provider = execute_ready(tmp_path, runner=runner)
    evidence_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in Path(result.evidence_dir).rglob("*")
        if path.is_file()
    )

    assert result.code == "RUNNER_ARTIFACT_EXPORT_FAILED"
    assert secret not in result.message
    assert secret not in evidence_text
    assert result.container_name in evidence_text
    assert f"{API_RUNNER_WORKDIR}/runtime/ci-runs/run-123/summary.json" in evidence_text
    assert "docker cp" in evidence_text


def test_exported_summary_stays_exact_but_lifecycle_evidence_is_redacted(tmp_path):
    artifacts = tmp_path / "container-artifacts"
    secret = "super-secret-value"
    write_container_artifacts(
        artifacts,
        status="failed",
        return_code=1,
        failed_nodeids=[f"test_secret={secret}"],
    )

    result, _runner, _provider = execute_ready(
        tmp_path, runner=FakeDockerRunner(artifacts)
    )
    standard_summary = (Path(result.run_dir) / "summary.json").read_text(encoding="utf-8")
    lifecycle_evidence = (Path(result.evidence_dir) / "result.json").read_text(encoding="utf-8")

    assert secret in standard_summary
    assert secret not in lifecycle_evidence
    assert "***" in lifecycle_evidence


def test_subprocess_runner_uses_argv_shell_false_and_redacts_output(tmp_path):
    calls = []

    class Completed:
        returncode = 3
        stdout = "token=hidden-value\n"
        stderr = ""

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return Completed()

    runner = SubprocessCommandRunner(run_factory=fake_run)
    result = runner.run(("docker", "version"), cwd=tmp_path, timeout_seconds=10)

    assert calls[0][0] == ["docker", "version"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == str(tmp_path.resolve())
    assert "hidden-value" not in result.stdout
    assert "***" in result.stdout


def test_cli_main_returns_zero_only_for_infrastructure_success(tmp_path):
    contexts = []

    class FakeLifecycle:
        def __init__(self, success):
            self.success = success

        def execute(self, context):
            contexts.append(context)
            return lifecycle.LifecycleResult(
                success=self.success,
                code="OK" if self.success else "RUNNER_LIFECYCLE_FAILED",
                message="done",
                container_name="runner",
                container_id="container-id",
                container_retained=not self.success,
                evidence_dir=tmp_path / "evidence",
                run_dir=tmp_path / "run",
                summary={"status": "failed", "return_code": 1},
            )

    env = {
        "WORKSPACE": str(tmp_path),
        "JOB_NAME": "Api Test",
        "BUILD_NUMBER": "9",
        "RUN_ID": "run-9",
    }

    assert api_runner_cli.main(
        ["execute"], env=env, cwd=tmp_path, lifecycle=FakeLifecycle(True)
    ) == 0
    assert api_runner_cli.main(
        ["execute"], env=env, cwd=tmp_path, lifecycle=FakeLifecycle(False)
    ) == 1
    assert [context.source_revision for context in contexts] == ["unknown", "unknown"]


def test_cli_output_redacts_summary_diagnostics(tmp_path, capsys):
    secret = "super-secret-value"

    class FakeLifecycle:
        def execute(self, context):
            return lifecycle.LifecycleResult(
                success=True,
                code="OK",
                message="done",
                container_name="runner",
                container_id="container-id",
                container_retained=False,
                evidence_dir=tmp_path / "evidence",
                run_dir=tmp_path / "run",
                summary={"status": "failed", "failed_nodeids": [f"test_token={secret}"]},
            )

    exit_code = api_runner_cli.main(
        ["execute"],
        env={"WORKSPACE": str(tmp_path), "RUN_ID": "run-redacted"},
        cwd=tmp_path,
        lifecycle=FakeLifecycle(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert secret not in output
    assert "***" in output
