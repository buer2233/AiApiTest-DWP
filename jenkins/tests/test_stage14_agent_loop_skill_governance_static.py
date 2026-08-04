"""Stage14 开发 loop 与 Skill 轻量化治理静态门禁。"""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

ACTIVE_GOVERNANCE_FILES = [
    *sorted(ROOT.rglob("AGENTS.md")),
    ROOT / "docs" / "自主开发流水线.md",
    ROOT / "project-info" / "project-skills-summary.md",
]

REMOVED_SKILLS = [
    "using-superpowers",
    "planning-with-files",
    "brainstorming",
    "product-requirements",
    "test-driven-development",
    "systematic-debugging",
    "receiving-code-review",
    "security-review",
    "subagent-driven-development",
    "django-tdd",
    "api-design",
    "python-patterns",
    "test-cases",
    "prototype-prompt-generator",
    "vue-best-practices",
    "frontend-design",
    "vue-router-best-practices",
    "vue-pinia-best-practices",
    "vue-testing-best-practices",
    "vue-debug-guides",
    "ckm:design-system",
]


def read(relative_path: str) -> str:
    """读取治理文件，缺失时给出清晰的仓库相对路径。"""
    path = ROOT / relative_path
    assert path.is_file(), f"缺少治理文件: {relative_path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ACTIVE_GOVERNANCE_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_active_governance_files_do_not_reference_removed_skills(path: Path):
    """失效 Skill 不得重新成为生效规则或推荐入口。"""
    content = path.read_text(encoding="utf-8")
    stale = [skill for skill in REMOVED_SKILLS if skill in content]

    assert not stale, f"{path.relative_to(ROOT)} 仍引用已移除 Skills: {stale}"


def test_root_rules_keep_dynamic_skill_selection_and_quality_gates_separate():
    """Skill 只能增强执行，当前会话清单与质量门禁必须解耦。"""
    content = read("AGENTS.md")

    for marker in [
        "当前会话提供的可用 Skills 清单",
        "按任务匹配",
        "Skill 不是质量门禁",
        "Skill 不可用",
        "不得跳过",
    ]:
        assert marker in content


def test_root_rules_define_executable_tdd_and_root_cause_debugging_protocols():
    """删除流程类 Skill 后，TDD 与根因排查行为仍必须可执行。"""
    content = read("AGENTS.md")

    for marker in [
        "RED -> GREEN -> REFACTOR",
        "确认失败原因是目标行为尚未实现",
        "最小实现",
        "不得通过删除或弱化断言",
        "稳定复现",
        "收集证据",
        "缩小范围",
        "验证根因",
        "最小修复",
        "相关回归",
    ]:
        assert marker in content


def test_root_rules_keep_loop_resume_and_independent_review_protocols():
    """长任务续接与独立复审不再依赖已删除的编排或审查 Skill。"""
    content = read("AGENTS.md")

    for marker in [
        "复杂任务",
        "执行计划",
        "中断恢复",
        "git status",
        "独立 review subagent",
        "实现者不得审查自己的改动",
        "按严重度",
        "文件和行号",
        "复审",
        "阻断问题清零",
    ]:
        assert marker in content


def test_root_rules_keep_original_loop_order_grading_and_checkpoints():
    """轻量化 Skill 不能改变阶段顺序、分级语义和固定检查点。"""
    content = read("AGENTS.md")

    ordered_stage_headings = [
        "### 1. 需求分析阶段",
        "### 2. 功能测试用例阶段",
        "### 3. UI 原型图阶段",
        "### 4. 后端开发阶段",
        "### 5. 前端开发阶段",
    ]
    positions = [content.index(heading) for heading in ordered_stage_headings]
    assert positions == sorted(positions)

    for marker in [
        "| XS |",
        "| S |",
        "| M / L |",
        "只能裁剪产物阶段，不能裁剪质量门禁",
        "任何档位都必须执行",
        "`N/A + 理由`",
        "需求澄清冻结",
        "架构影响评估",
        "API 契约冻结",
        "容器化兼容检查",
    ]:
        assert marker in content


def test_ui_applicability_and_na_paths_are_consistent_across_stage_rules():
    """UI 原型适用与 N/A 两个分支必须都能合法进入前端阶段。"""
    expected_markers = {
        "AGENTS.md": [
            "UI 阶段适用时",
            "UI 阶段评估为 `N/A` 时",
            "同名 UI 适用性说明",
        ],
        "front-end/AGENTS.md": [
            "UI 阶段适用时",
            "UI 阶段评估为 `N/A` 时",
            "同名 UI 适用性说明",
            "既有视觉基线",
        ],
        "project-info/UI/AGENTS.md": [
            "UI 阶段适用时",
            "UI 阶段评估为 `N/A` 时",
            "同名 UI 适用性说明",
            "无需伪造原型",
        ],
    }

    for relative_path, markers in expected_markers.items():
        content = read(relative_path)
        missing = [marker for marker in markers if marker not in content]
        assert not missing, f"{relative_path} 的 UI 适用性分支不完整: {missing}"


def test_tdd_protocol_is_enforced_in_each_executable_implementation_module():
    """根、后端、前端、执行器和 Jenkins 都必须要求有效 RED 与完整循环。"""
    expected_markers = {
        "AGENTS.md": ["确认失败原因是目标行为尚未实现", "RED -> GREEN -> REFACTOR"],
        "back-end/AGENTS.md": ["目标行为缺失", "RED -> GREEN -> REFACTOR"],
        "front-end/AGENTS.md": ["目标行为缺失", "RED -> GREEN -> REFACTOR"],
        "api-test/AGENTS.md": ["目标行为缺失", "RED -> GREEN -> REFACTOR"],
        "jenkins/AGENTS.md": ["目标行为缺失", "RED -> GREEN -> REFACTOR"],
    }

    for relative_path, markers in expected_markers.items():
        content = read(relative_path)
        missing = [marker for marker in markers if marker not in content]
        assert not missing, f"{relative_path} 的 TDD 协议不完整: {missing}"


def test_independent_review_and_rereview_are_enforced_in_all_review_rules():
    """根、前后端与自主流水线必须共同保留独立审查和复审。"""
    expected_markers = {
        "AGENTS.md": ["独立 review subagent", "同一名独立 reviewer", "阻断问题清零"],
        "back-end/AGENTS.md": ["独立 review subagent", "同一 reviewer", "阻断问题清零"],
        "front-end/AGENTS.md": ["独立 review subagent", "同一 reviewer", "阻断问题清零"],
        "docs/自主开发流水线.md": ["独立 review subagent", "同一 reviewer", "阻断问题清零"],
    }

    for relative_path, markers in expected_markers.items():
        content = read(relative_path)
        missing = [marker for marker in markers if marker not in content]
        assert not missing, f"{relative_path} 的独立复审协议不完整: {missing}"


def test_rtm_evidence_and_jenkins_entrypoint_contracts_remain_in_force():
    """Skill 重构不得弱化可追溯、证据或平台环境唯一入口。"""
    root = read("AGENTS.md")
    autonomous = read("docs/自主开发流水线.md")

    for marker in [
        "需求名-可追溯矩阵.md",
        "Jenkins artifact",
        "pytest 实际运行输出",
        "Playwright 运行结果",
        "平台环境唯一入口",
        "scripts/trigger-platform-bootstrap.ps1",
        "scripts/trigger-platform-bootstrap.sh",
    ]:
        assert marker in root
    for marker in ["RTM", "测试证据", "验收包", "环境 Job"]:
        assert marker in autonomous


def test_stage_rules_replace_removed_skills_with_concrete_behavior():
    """各阶段必须直接描述输入、决策、测试和实现约束。"""
    expected_markers = {
        "project-info/demand/AGENTS.md": ["可行方案", "取舍", "假设", "熔断"],
        "project-info/test_case/AGENTS.md": ["每个 AC", "正常场景", "异常场景", "边界值"],
        "project-info/UI/AGENTS.md": ["任务匹配", "高保真", "区域语义拆解", "可访问性"],
        "back-end/AGENTS.md": ["资源语义", "统一错误模型", "幂等", "OpenAPI", "python-testing"],
        "front-end/AGENTS.md": [
            "<script setup lang=\"ts\">",
            "typed props",
            "Pinia",
            "TanStack Query",
            "路由鉴权",
            "可访问性",
            "Vitest",
            "Playwright",
        ],
        "jenkins/AGENTS.md": ["RED -> GREEN -> REFACTOR", "失败测试"],
        "docker/AGENTS.md": ["静态配置验证", "Platform Bootstrap Job"],
    }

    for relative_path, markers in expected_markers.items():
        content = read(relative_path)
        missing = [marker for marker in markers if marker not in content]
        assert not missing, f"{relative_path} 缺少行为规则: {missing}"


def test_skill_summary_distinguishes_session_availability_from_disk_residue():
    """Skill 总结必须是动态使用说明，而不是会过期的硬编码门禁。"""
    content = read("project-info/project-skills-summary.md")

    for marker in [
        "当前会话",
        "唯一事实来源",
        "磁盘存在",
        "不代表当前可调用",
        "imagegen",
        "drawio-skill",
        "python-testing",
        "ui-ux-pro-max",
        "design-system",
    ]:
        assert marker in content


def test_claude_files_remain_single_line_agent_rule_references():
    """CLAUDE.md 只引用同目录 AGENTS.md，避免双份规则漂移。"""
    for path in ROOT.rglob("CLAUDE.md"):
        assert path.read_text(encoding="utf-8").strip() == "@AGENTS.md"
