# 开发 Loop 轻量化重构 Stage14 可追溯矩阵

| AC | 测试用例 | 实现位置 | 验收状态 |
| --- | --- | --- | --- |
| AC1.1 | TC-ST14-SKILL-001 | 根及嵌套 `AGENTS.md`、`docs/自主开发流水线.md`、`project-info/project-skills-summary.md` | 通过：Stage14 静态门禁 |
| AC1.2 | TC-ST14-SKILL-001 | 根 `AGENTS.md` Skill 使用策略、Skill 总结 §1-§2 | 通过：Stage14 静态门禁 |
| AC1.3 | TC-ST14-SKILL-002 | 同名盘点发现、Skill 总结 §1/§3 | 通过：盘点与静态门禁 |
| AC2.1 | TC-ST14-LOOP-001 | 根 `AGENTS.md` 固定开发循环、`docs/自主开发流水线.md` | 通过：阶段顺序与分级静态门禁 |
| AC2.2 | TC-ST14-TDD-001 | 根、`api-test`、`back-end`、`front-end`、`jenkins` 的 `AGENTS.md` | 通过：跨模块 TDD 静态门禁 |
| AC2.3 | TC-ST14-GATE-001 | 根 `AGENTS.md` 裁剪规则与四项检查点 | 通过：精确语义静态门禁 |
| AC3.1 | TC-ST14-BEHAVIOR-001 | `project-info/demand`、`project-info/test_case`、`project-info/UI`、`back-end`、`front-end` 的 `AGENTS.md` | 通过：行为规则静态门禁 |
| AC3.2 | TC-ST14-SKILL-003 | 根、UI、前端 `AGENTS.md` 与 Skill 总结 | 通过：Stage14 静态门禁 |
| AC3.3 | TC-ST14-SKILL-003 | 根、架构资料 `AGENTS.md` 与 Skill 总结 | 通过：Stage14 静态门禁 |
| AC4.1 | TC-ST14-REVIEW-001 | 根、前后端 `AGENTS.md`、自主流水线、同名独立审查记录 | 通过：已执行独立首轮审查，规则静态门禁通过 |
| AC4.2 | TC-ST14-STATIC-001 | `jenkins/tests/test_stage14_agent_loop_skill_governance_static.py` | 通过：增强后 `24 passed` |
| AC4.3 | TC-ST14-REVIEW-001 | 同名独立审查记录 | 通过：同一 reviewer 最终复审无阻断或中等问题 |
