"""Stage13 Task 6 验证证据留存与历史资料链接静态门禁。"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
PROJECT_INFO = ROOT / "project-info"
RETIRED_EVIDENCE_PATH = re.compile(r"(?:tests[\\\\/])?evidence[\\\\/]", re.IGNORECASE)
LOCAL_WORK_RECORD_REFERENCE = re.compile(
    r"(?:\.planning[\\/]|task-\d+(?:-[a-z0-9]+)*-(?:report|review|rereview)\.md)",
    re.IGNORECASE,
)
STAGE13_CASE_DIR = PROJECT_INFO / "test_case" / "Stage13-Jenkins统一平台环境启动流水线"
STAGE13_RTM = STAGE13_CASE_DIR / "平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵.md"
STAGE13_ACCEPTANCE = STAGE13_CASE_DIR / "平台环境准备-Jenkins统一平台环境启动流水线-验收包.md"


def test_root_agent_rules_keep_runtime_evidence_out_of_git():
    """实际验证产物只能进入 Jenkins 或任务期临时目录，不能提交仓库。"""
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    for marker in ["Jenkins artifact", "`docs/`", "任务完成后清理", "严禁提交 Git"]:
        assert marker in content


def test_project_info_has_no_links_to_retired_evidence_directories():
    """历史验收资料不得再引用已从 Git 清理的 evidence 目录。"""
    stale_links: list[str] = []
    for path in PROJECT_INFO.rglob("*.md"):
        if RETIRED_EVIDENCE_PATH.search(path.read_text(encoding="utf-8")):
            stale_links.append(path.relative_to(ROOT).as_posix())

    assert not stale_links, f"历史资料仍含已清理证据路径: {stale_links}"


def test_stage13_rtm_uses_the_actual_final_jenkins_backend_coverage():
    """Stage13 RTM 必须记录 Build #24 的真实后端覆盖率，而非本地结果。"""
    content = STAGE13_RTM.read_text(encoding="utf-8")

    assert "95%" not in content
    assert re.search(r"Jenkins Build #24 artifact[^\n]*230 passed / 91%", content)


def test_stage13_final_build_evidence_is_archived_by_jenkins_not_local_work_records():
    """最终验收资料只能引用 Jenkins artifact 与已提交 Stage13 资料。"""
    for path in [STAGE13_RTM, STAGE13_ACCEPTANCE]:
        content = path.read_text(encoding="utf-8")

        assert not LOCAL_WORK_RECORD_REFERENCE.search(content)
        for build_number in [22, 23, 24]:
            assert f"Jenkins Build #{build_number} artifact" in content

    acceptance_content = STAGE13_ACCEPTANCE.read_text(encoding="utf-8")
    assert "95%" not in acceptance_content
    assert re.search(
        r"Jenkins Build #24 artifact[^\n]*230 passed / 91%", acceptance_content
    )
