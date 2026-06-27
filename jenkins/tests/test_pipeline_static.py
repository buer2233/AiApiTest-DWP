"""Jenkins 三个独立 Pipeline 静态结构测试（F8 / AC8.1-AC8.5）。

不启动真实 Jenkins，直接读取 Groovy 脚本，验证：参数定义、模式映射、
跨平台分支、ci_runner 委托、workspace 相对路径与无明文凭据。
"""
import re
from pathlib import Path

JENKINS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = JENKINS_ROOT / "scripts"
LIB_COMMON = SCRIPTS / "lib" / "pipeline-common.groovy"

PIPELINES = {
    "daily-full": SCRIPTS / "daily-full-pipeline.groovy",
    "module-rerun": SCRIPTS / "module-rerun-pipeline.groovy",
    "failed-rerun": SCRIPTS / "failed-rerun-pipeline.groovy",
}

JENKINSFILES = {
    "daily-full": JENKINS_ROOT / "Jenkinsfile.daily-full",
    "module-rerun": JENKINS_ROOT / "Jenkinsfile.module-rerun",
    "failed-rerun": JENKINS_ROOT / "Jenkinsfile.failed-rerun",
}


def _read(path):
    return path.read_text(encoding="utf-8")


def _with_common(name):
    """pipeline 自身 + 公共库（执行逻辑在公共库），合并后做契约断言。"""
    return _read(PIPELINES[name]) + "\n" + _read(LIB_COMMON)


# --- AC8.1：三个 pipeline + 公共库就位 ---
def test_three_pipelines_and_common_exist():
    for path in PIPELINES.values():
        assert path.exists(), path
    assert LIB_COMMON.exists()


# --- AC8.2：daily-full 定时触发 + 全量 + retry-mode none ---
def test_daily_full_cron_and_full_none_mode():
    content = _read(PIPELINES["daily-full"])
    assert "cron(" in content
    assert "RETRY_MODE=none" in content
    assert "CASE_PATH=test_case" in content


# --- AC8.3：module-rerun 接收 CASE_PATH 且以 module 模式调用 ---
def test_module_rerun_receives_case_path_and_module_mode():
    content = _read(PIPELINES["module-rerun"])
    assert "CASE_PATH" in content
    assert "params.CASE_PATH" in content
    assert "RETRY_MODE=module" in content


# --- AC8.4：failed-rerun 支持 selected/all-failed + node ids ---
def test_failed_rerun_supports_selected_and_all_failed():
    content = _read(PIPELINES["failed-rerun"])
    assert "RETRY_MODE" in content
    assert "selected" in content
    assert "all-failed" in content
    assert "PYTEST_NODE_IDS" in content


# --- AC8.5：统一委托 ci_runner，经 --from-jenkins-env ---
def test_all_pipelines_delegate_to_ci_runner():
    for name in PIPELINES:
        combined = _with_common(name)
        assert "tools.ci_runner" in combined, name
        assert "--from-jenkins-env" in combined, name


# --- AC8.5：不复制 pytest 执行 / 重试 / node id / Allure 解析逻辑 ---
def test_pipelines_do_not_embed_execution_logic():
    for name in PIPELINES:
        combined = _with_common(name)
        assert "import pytest" not in combined, name
        assert "--reruns" not in combined, name
        assert "lastfailed" not in combined, name
        assert "normalize_nodeids" not in combined, name


# --- AC8.5：跨平台分支集中在公共库 ---
def test_common_has_cross_platform_branch():
    content = _read(LIB_COMMON)
    assert "isUnix()" in content
    assert "sh " in content
    assert "bat " in content


# --- AC8.5：workspace 相对路径，无本机绝对盘符路径 ---
def test_common_uses_relative_workspace_paths():
    content = _read(LIB_COMMON)
    assert "api-test" in content
    assert not re.search(r"[A-Za-z]:\\", content)


# --- AC8.5：不含明文凭据 / token / 真实 URL ---
def test_no_plaintext_credentials_or_urls():
    for path in list(PIPELINES.values()) + [LIB_COMMON] + list(JENKINSFILES.values()):
        lowered = _read(path).lower()
        assert "token" not in lowered, path
        assert "http://" not in lowered, path
        assert "https://" not in lowered, path
        assert "password=" not in lowered, path


# --- 归档与发布报告集中在公共库 ---
def test_common_archives_and_publishes_reports():
    content = _read(LIB_COMMON)
    assert "archiveArtifacts" in content
    assert "allure" in content


# --- 三个 job 入口 Jenkinsfile 在 node 上下文 load 对应 pipeline ---
def test_jenkinsfiles_load_their_pipeline_inside_node():
    for name, jf in JENKINSFILES.items():
        assert jf.exists(), jf
        content = _read(jf)
        assert "node" in content
        assert f"jenkins/scripts/{name}-pipeline.groovy" in content


# --- 旧单一 pipeline 已被拆分移除 ---
def test_legacy_single_pipeline_removed():
    assert not (SCRIPTS / "api-test-pipeline.groovy").exists()
