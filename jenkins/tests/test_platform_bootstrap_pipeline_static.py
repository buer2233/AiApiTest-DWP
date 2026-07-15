"""Stage13 Task 3B 环境 Jenkins Pipeline 静态契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JENKINSFILE = ROOT / "jenkins" / "Jenkinsfile.platform-bootstrap"
PIPELINE = ROOT / "jenkins" / "scripts" / "platform-bootstrap-pipeline.groovy"


def read_required(path: Path) -> str:
    assert path.is_file(), f"missing required Task3B file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def brace_block(source: str, token: str) -> str:
    start = source.index(token)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unclosed block for {token}")


def local_mounted_copy_block(source: str) -> str:
    """返回加载完成后、负责复制源码的第二个本地挂载分支。"""
    token = "if (env.LOCAL_WORKSPACE_REPO == 'true')"
    first = source.index(token)
    second = source.index(token, first + len(token))
    return brace_block(source[second:], token)


def test_pipeline_has_only_two_boolean_parameters_and_disables_concurrency():
    source = read_required(JENKINSFILE) + "\n" + read_required(PIPELINE)

    assert "disableConcurrentBuilds()" in source
    assert "booleanParam(name: 'build_all', defaultValue: true" in source
    assert "booleanParam(name: 'run_full_tests', defaultValue: false" in source
    assert source.count("booleanParam(") == 2
    for forbidden in ["string(", "text(", "choice(", "password("]:
        assert forbidden not in source


def test_pipeline_uses_fixed_seven_stage_order_and_local_or_scm_checkout():
    jenkinsfile = read_required(JENKINSFILE)
    pipeline = read_required(PIPELINE)
    source = jenkinsfile + "\n" + pipeline
    stages = [
        "Checkout/Workspace",
        "Bootstrap Preflight",
        "Dependency Assurance",
        "Deploy",
        "Health",
        "Tests",
        "Archive & Summary",
    ]

    offsets = [source.index(f"stage('{stage}')") for stage in stages]
    assert offsets == sorted(offsets)
    assert "LOCAL_WORKSPACE_REPO" in jenkinsfile
    assert "checkout scm" in jenkinsfile
    assert "load 'jenkins/scripts/platform-bootstrap-pipeline.groovy'" in jenkinsfile
    assert jenkinsfile.index("LOCAL_WORKSPACE_REPO") < jenkinsfile.index("checkout scm")


def test_pipeline_is_cross_platform_and_delegates_all_logic_to_python_cli():
    pipeline = read_required(PIPELINE)

    assert "isUnix()" in pipeline
    assert "sh(" in pipeline or "sh " in pipeline
    assert "bat(" in pipeline or "bat " in pipeline
    for command in ["preflight", "assure-dependencies", "deploy", "health", "test", "summary"]:
        assert command in pipeline
    assert "platform_bootstrap_cli.py" in pipeline
    assert "python3 jenkins/scripts/platform_bootstrap_cli.py" in pipeline
    for forbidden in [
        "docker compose",
        "docker build",
        "curl ",
        "pip install",
        "npm install",
        "Authorization",
        "JENKINS_API_TOKEN",
        "JENKINS_USERNAME",
    ]:
        assert forbidden not in pipeline


def test_pipeline_always_summarizes_archives_and_degrades_allure_to_warning():
    source = read_required(JENKINSFILE) + "\n" + read_required(PIPELINE)

    assert "finally" in source
    finally_offset = source.index("finally")
    summary_offset = source.index("stage('Archive & Summary')")
    assert finally_offset < summary_offset
    assert "archiveArtifacts" in source
    assert "allowEmptyArchive: true" in source
    assert "allure(" in source
    assert "catch (Throwable" in source
    assert "warning" in source.lower()


def test_pipeline_uses_per_build_evidence_directory_and_no_destructive_commands():
    source = read_required(JENKINSFILE) + "\n" + read_required(PIPELINE)

    assert "BUILD_TAG" in source
    assert "runtime/platform-bootstrap" in source
    assert "PLATFORM_BOOTSTRAP_EVIDENCE_DIR" in source
    for forbidden in [
        "down -v",
        "volume rm",
        "migration",
        "migrate",
        "collectstatic",
        "init_admin",
        "rollback",
        "chmod 666",
    ]:
        assert forbidden not in source.lower()


def test_checkout_fallback_creates_evidence_directory_and_does_not_archive_raw_exception():
    jenkinsfile = read_required(JENKINSFILE)

    assert "dir(fallbackEvidenceDir)" in jenkinsfile
    fallback = jenkinsfile[jenkinsfile.index("if (!pipelineLoaded)") :]
    assert "failure.getMessage()" not in fallback
    assert "platform-bootstrap-summary.json" in fallback


def test_archive_failures_preserve_primary_and_fail_when_no_primary_exists():
    jenkinsfile = read_required(JENKINSFILE)
    pipeline = read_required(PIPELINE)

    assert "archiveFailure" in pipeline
    assert "try {" in pipeline[pipeline.index("stage('Archive & Summary')") :]
    assert "catch (Throwable archive" in pipeline
    assert "primaryFailure == null" in pipeline
    assert "fallbackArchiveFailure" in jenkinsfile
    assert "catch (Throwable archive" in jenkinsfile
    assert jenkinsfile.rindex("throw failure") > jenkinsfile.index("fallbackArchiveFailure")


def test_local_mounted_mode_validates_and_enters_configured_workspace_before_load():
    jenkinsfile = read_required(JENKINSFILE)

    assert "AIAPITEST_LOCAL_WORKSPACE" in jenkinsfile
    assert "fileExists" in jenkinsfile
    assert "dir(localWorkspace)" in jenkinsfile
    local_block = jenkinsfile[
        jenkinsfile.index("LOCAL_WORKSPACE_REPO") : jenkinsfile.index("else {")
    ]
    assert local_block.index("dir(localWorkspace)") < jenkinsfile.index(
        "load 'jenkins/scripts/platform-bootstrap-pipeline.groovy'"
    )


def test_local_mounted_mode_runs_durable_steps_from_writable_workspace():
    """挂载源码目录只用于加载和 CLI 的 cd 目标，不能承载 Jenkins durable @tmp。"""
    jenkinsfile = read_required(JENKINSFILE)
    pipeline = read_required(PIPELINE)

    assert "PLATFORM_BOOTSTRAP_SOURCE_WORKSPACE" in pipeline
    assert 'cd \\"' in pipeline
    assert pipeline.index('cd \\"') < pipeline.index("platform_bootstrap_cli.py")
    assert "--exclude=.git" in jenkinsfile
    for ignored_runtime_path in [".pytest_tmp*", "runtime", "node_modules", ".idea"]:
        assert ignored_runtime_path in jenkinsfile
    assert "dir(localWorkspace) {\n                pipelineScript.call()" not in jenkinsfile


def test_windows_local_copy_propagates_robocopy_failure_with_delayed_expansion():
    """robocopy 的 8 及以上错误码必须原样传给 Jenkins，0 至 7 才可归零。"""
    copy_block = local_mounted_copy_block(read_required(JENKINSFILE))

    robocopy_offset = copy_block.index("robocopy")
    enable_offset = copy_block.index("setlocal EnableDelayedExpansion")
    capture_offset = copy_block.index('set "ROBOCOPY_EXIT=!ERRORLEVEL!"')
    failure_offset = copy_block.index(
        "if !ROBOCOPY_EXIT! GEQ 8 exit /B !ROBOCOPY_EXIT!"
    )
    success_offset = copy_block.index("exit /B 0", failure_offset)

    assert enable_offset < robocopy_offset < capture_offset < failure_offset < success_offset
    assert "%ERRORLEVEL%" not in copy_block


def test_windows_local_copy_excludes_generated_and_runtime_directories():
    """Windows 必须与 Linux 使用同一组本地生成目录排除项。"""
    copy_block = local_mounted_copy_block(read_required(JENKINSFILE))
    robocopy_line = next(
        line.strip() for line in copy_block.splitlines() if "robocopy" in line
    )

    assert "/XD .git .pytest_tmp* .tmp runtime report node_modules .idea" in robocopy_line


def test_local_mounted_copy_cleans_only_writable_workspace_before_copy():
    """每次复制前清理 Jenkins workspace，挂载源码加载块不得执行删除。"""
    jenkinsfile = read_required(JENKINSFILE)
    token = "if (env.LOCAL_WORKSPACE_REPO == 'true')"
    mounted_load_block = brace_block(jenkinsfile, token)
    copy_block = local_mounted_copy_block(jenkinsfile)

    assert "deleteDir()" not in mounted_load_block
    assert copy_block.count("deleteDir()") == 1
    cleanup_offset = copy_block.index("deleteDir()")
    assert cleanup_offset < copy_block.index("tar -C")
    assert cleanup_offset < copy_block.index("robocopy")


def test_summary_step_exception_still_reaches_archive_allure_and_preserves_priority():
    pipeline = read_required(PIPELINE)
    archive_stage = brace_block(pipeline, "stage('Archive & Summary')")

    assert "catch (Throwable summaryProblem)" in archive_stage
    assert archive_stage.index("runCliStatus('summary'") < archive_stage.index(
        "catch (Throwable summaryProblem)"
    )
    assert archive_stage.index("catch (Throwable summaryProblem)") < archive_stage.index(
        "archiveArtifacts"
    )
    assert archive_stage.index("archiveArtifacts") < archive_stage.index("allure(")
    assert pipeline.index("if (primaryFailure != null)") < pipeline.index(
        "if (summaryFailure != null)"
    ) < pipeline.index("if (archiveFailure != null)")


def test_checkout_stage_does_not_nest_remaining_six_stages_in_local_mode():
    jenkinsfile = read_required(JENKINSFILE)
    checkout_blocks = []
    offset = 0
    token = "stage('Checkout/Workspace')"
    while token in jenkinsfile[offset:]:
        absolute = jenkinsfile.index(token, offset)
        checkout_blocks.append(brace_block(jenkinsfile[absolute:], token))
        offset = absolute + len(token)

    assert checkout_blocks
    assert all("pipelineScript.call()" not in block for block in checkout_blocks)
    assert "dir(localWorkspace)" in jenkinsfile
    assert jenkinsfile.rindex("pipelineScript.call()") > max(
        jenkinsfile.index(block) for block in checkout_blocks
    )


def test_checkout_fallback_catches_summary_dir_write_and_archive_independently():
    jenkinsfile = read_required(JENKINSFILE)
    fallback = jenkinsfile[jenkinsfile.index("if (!pipelineLoaded)") :]

    assert "fallbackSummaryFailure" in fallback
    assert "catch (Throwable summaryProblem)" in fallback
    assert "fallbackArchiveFailure" in fallback
    assert "catch (Throwable archiveProblem)" in fallback
    assert fallback.index("catch (Throwable summaryProblem)") < fallback.index(
        "archiveArtifacts"
    )
    assert jenkinsfile.rindex("throw failure") > fallback.index("archiveArtifacts")
