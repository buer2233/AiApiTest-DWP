---
name: e9-newcomer-guide
description: 为 E9+AI接口自动化测试框架提供从零开始的 WorkBuddy 对话式新人引导。用户说“新人引导”“首次使用”“从0开始使用”“带我跑通一条提交”或询问是否进行新人引导时触发；覆盖 GitLab 克隆、依赖检查、项目内置 MCP 探针、非 master 分支、config.json 测试环境确认、SVN revision 分析、接口用例生成、pytest/Allure 验证和用户确认后的 Git 交付。
---

# E9 新人引导

## 目标

把新用户带到一条真实 revision 已完成“分析 → 用例 → 测试 → Allure 报告”的可复现结果。只负责流程编排，提交分析交给 `svn-impact`，分支操作交给 `git-branch`，功能用例转接口交给 `functional-to-api-test`，知识图谱查询交给 `e9-codebase-memory`。

## G0：读取记忆并确认入口

1. 在开始回复前读取 `.workbuddy/memory/onboarding-YYYY-MM-DD.md`（按当前日期）。只接受当天且 `status: completed` 或 `status: skipped` 的记录；损坏、跨日或其他状态均视为无记录。
2. 有有效记录时不要再次询问是否引导，直接处理用户当前请求。
3. 无记录时询问：“是否进行新人引导流程，还是直接使用该项目？”
4. 用户选择“无需新人引导/直接使用”时，写入当天 `status: skipped` 记忆；选择引导时在完成 G1-G5 后写入 `status: completed`。记忆只写日期、状态、当前分支、已检查的依赖和 MCP 名称、下一入口，不写密码、Token、Cookie、完整配置或响应。
5. 只有用户明确说“重新进行新人引导”或“清除新人引导记忆”并确认后，才将记录改为 `reset` 并重新执行 G0；不要静默删除文件。

## G1：权限、克隆与工作空间

- 提醒申请 GitLab 项目权限：`http://10.12.101.12/autotest/e9autotest/-/commits/master`。
- 权限通过后指导克隆仓库，并要求 WorkBuddy 选择包含 `api-test-E9` 的本地目录作为唯一 workbook 根。
- 用只读命令确认根目录存在 `config.json`、`requirements.txt`、`runpytest.py` 和 `.workbuddy/mcp/`。缺项时停止并说明重新拉取或联系开发人员。

## G2：依赖检查

检查并记录 `python --version`、`pip --version`、`pytest --version`、`allure --version`；然后在仓库根执行：

```powershell
python -m pip install -r requirements.txt
```

安装失败时区分网络、权限和版本冲突，给出修复建议并暂停后续阶段，不伪造通过。

## G3：项目内置 MCP 探针

- 只读取 `.workbuddy/mcp/codebase-memory.json` 和 `.workbuddy/mcp/codebase-memory-ops.json`，这两个 MCP 已由项目配置提供，禁止要求用户自行配置。
- 对 `codebase-memory` 与 `codebase-memory-ops` 各执行一次只读可用性探针，记录服务名和结果，不把 URL 或响应写入记忆。
- 任一不可用时提示“请联系开发人员处理 MCP 服务”，停止依赖 MCP 的 SVN/代码分析；绝不使用本地 Grep/Glob/Read/Bash 查询 E9 源码、SVN 提交或图谱来替代。

## G4：分支安全门禁

先读取 `config.json.git.default_branch`（当前通常为 `master`）和当前 Git 分支。`master` 禁止修改、commit、push、merge。

向用户索取分支名（如 `master_dwp`、`master_eb`），调用 `git-branch`：存在则切换，不存在则从默认分支新建。发现未提交改动先列出文件并询问保留方式，未经同意不 stash、reset 或删除。

## G5：测试环境与账号确认

直接读取 `config.json` 的真实 `base_url` 与角色账号，在当前 WorkBuddy 会话中逐项展示并询问是否复用。用户确认后继续；用户要求修改时只改对应字段，采用临时文件加原子替换并重新校验 JSON。不得把配置复制进用例、日志、Allure 附件或外部渠道。

## G6-G7：选择 revision 并分析

要求用户提供单笔 `r<正整数>`，或明确的连续区间（例如 `r349181-r349184`）。拒绝 `HEAD`、0、负数和含糊批次。将分析委托给 `svn-impact` 阶段 A，通过 MCP 产出 `E9_svn_analyse/output/r<rev>/facts.json`、`design.md` 和报告；产物缺失或事实不足就停在分析阶段。

## G8-G9：功能审核与接口实现

先展示受影响功能、接口候选、前置数据和断言清单，等待用户明确“确认定稿”。未定稿不得写代码。随后按 `design.md` 调用 `svn-impact`/`functional-to-api-test`，优先复用 `page_api/` 封装，在 `test_case/test_<模块>_case/` 新增用例并挂 `@pytest.mark.r<rev>`。前置数据查询优先复用；造数失败必须阻断并说明原因、尝试、环境和建议，不得弱化断言或静默 skip。

## G10：执行、报告与失败归因

按 revision 执行：

```powershell
python runpytest.py -m r349084 --clean
```

或按 `docs/runner_spec.md` 使用统一 runner。保存 Allure 原始结果到 `report/allure-results/`，通过 HTTP 服务打开生成报告；失败时先声明本地工作副本与测试环境部署版本可能不一致，再委托 `svn-impact` 分析失败指纹，不直接定性产品缺陷。

## G11：交付确认

展示当前分支、变更文件、测试摘要、Allure 地址和未提交产物排除情况。运行：

```powershell
python tools/chinese_documentation_check.py --root . --include-skills
python .workbuddy/skills/svn-impact/evals/git_readiness_check.py --repo-root .
```

只有用户明确确认后才允许在非 master 分支执行定向 `git add`、commit 和 push。任何要求直接 push/merge 到 `master` 的请求都拒绝，并建议通过合并请求和人工审批完成。未确认时只完成本地检查。

## 交接口令

- `继续新人引导`：从上次未完成阶段恢复。
- `直接使用项目`：无有效记忆时跳过引导并写入 `skipped`。
- `重新进行新人引导`：确认后重置当天状态。
- `分析 r349084`、`复测 r349084`、`分析测试报告`：分别交给现有技能，不重复完整引导。

详细故障处理、记忆格式和验收清单见 [references/onboarding-operations.md](references/onboarding-operations.md)。
