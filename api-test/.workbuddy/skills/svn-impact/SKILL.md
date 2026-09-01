---
name: svn-impact
description: E9+AI接口自动化测试框架中的单笔或多笔 SVN 提交影响分析、联合设计、功能测试用例设计、人工审核、接口自动化、前置测试数据构建、复测、接口覆盖校验、用例选取和 Allure 失败报告分析工作流。用户提及单个 revision（如 r349084）、多个 revision、Revision A 到 Revision B、显式 revision 集合、批次总结说明、快速测试、生成功能测试用例、审核功能用例、按方案实现接口自动化、复测、接口覆盖校验、按功能关键词选用例或分析测试报告时使用。单笔和批次共用同一生命周期与证据规则。
---

# E9+AI接口自动化测试框架：影响分析与定向回归

本文件是 E9 影响分析和接口自动化的唯一操作入口。workbook 打开根即 `api-test-E9/`（接口自动化框架 + 本技能）。E9 源码和知识图谱由外部 MCP 服务（codebase-memory）维护，所有代码分析操作统一通过 MCP 完成，本仓库只作为调用方。除特别说明外，命令均相对 `api-test-E9/` 给出；不得写死本机绝对路径。

完整执行流和节点契约见同目录 `flow.md`；单笔与批次共用规则见 `references/common-analysis-contract.md`。功能用例设计必须读取 `references/functional-case-design.md`，前置数据读取 `references/prepare-data.md` 和 `../functional-to-api-test/references/test-data-reuse.md`，报告分析读取 `references/allure-analysis.md`。所有模块的阶段 B 必须先查询并复用当前环境数据，确认缺失后才反查和尝试造数。修改本 SKILL、前置数据流程或 MCP 反查规则时，必须同步检查流程图和对应 Evals。

## 范围与安全

### E9 代码查询硬性禁令（最高优先级，违反即流程错误）

**绝对禁止**使用任何本地工具直接查询 E9 源代码、SVN 提交信息或 CBM 知识图谱：

| 禁止行为 | 禁止使用的工具 | 说明 |
|---------|---------------|------|
| 本地搜索 E9 代码 | `Grep`、`Glob`、`Bash`（`grep`/`find`/`rg` 等） | 不得以任何关键词搜索 E9 源码目录 |
| 本地读取 E9 文件 | `Read`、`Bash`（`cat`/`less` 等） | 不得直接打开 E9 项目的任何源文件 |
| 本地 SVN 操作 | `Bash`（`svn log`/`svn diff`/`svn info` 等） | 不得执行任何 SVN 命令查询提交信息 |
| 本地图谱查询 | `Bash`（`codegraph` 等） | 不得绕过 MCP 直接查询本地或远程图谱 |
| 绕过 MCP 的 HTTP 查询 | `WebFetch`、`mcp__fetch__fetch`、`Bash`（`curl` 到图谱 API） | 不得绕过 `codebase-memory` MCP 直接调图谱 HTTP 接口 |

**唯一合法路径**：所有 E9 代码分析、SVN 变更查询、调用链追踪、符号搜索**必须且仅能**通过以下 MCP 完成：

- **代码查询** → `codebase-memory` MCP（端点 `http://10.20.62.239:9750/mcp`）
- **图谱运维** → `codebase-memory-ops` MCP（端点 `http://10.20.62.239:9750/servers/e9-ops/mcp`）

违反上述禁令的后果：分析结果不可信（本地副本可能过期）、安全风险（暴露 SVN 路径或凭据）、流程审计失败。**任何时候发现自己在用 Grep/Glob/Read/Bash 查 E9 代码，立即停止并改用 MCP。**

### 其他范围与安全

- 本仓库（`api-test-E9/`）是主要开发区域，也是独立 Git 仓库；实现封装、用例、工具和本技能都在这里。
- E9 源码分析**仅能**通过 MCP（codebase-memory）完成。**绝对禁止**使用 Grep/Glob/Read/Bash 等本地工具查询 E9 代码、SVN 提交信息或 CBM 知识图谱（详见上方禁令表）。
- `E9_svn_analyse/svn_analyse/` 仅在接入既有分析能力确有必要时修改，不做无关重构。
- 需求说明和计划书已冻结。发现需求缺口时，在 `E9_svn_analyse/docs/` 对应分期的进度文档登记变更申请（三期 → `E9_svn_analyse/docs/三期开发/三期开发进度.md`），等待人工评审。
- 不将账号、密码、cookie、token、完整请求头或完整响应体写入 `output/`、日志、报告或 Allure 附件。
- 测试环境凭据文件 `config.json`、`test_data/account.json` 按三期已批准变更（撤回「不提交真实凭据」红线）允许提交团队内部 GitLab，同事 clone 即用；`report/`、`runtime/`、`logs/`、`.workbuddy/memory/` 仍禁止提交。
- 用例依赖的测试数据统一放 `test_data/<模块名>/`，纳入 Git 管理；`runtime/` 只放可重新生成的临时产物。数据文件只含 ID、字段名、探测值等业务标识，不含凭据。
- 测试失败时先声明：本地工作副本版本可能与测试环境部署版本不一致。未确认部署版本时，不把断言失败定性为产品缺陷。

## 全流程总览

用户给出单个 revision 或批次 revision 集合后，完整链条按序推进；每一步都有独立触发词，也可以从任一环节切入。单笔与批次都必须遵守 `references/common-analysis-contract.md`，批次只在阶段 A 增加逐笔编排和联合聚合。用户要求"端到端 / 全流程 / 一条龙"时，按顺序逐步执行，每步在对应阶段边界汇报后继续。

1. 阶段 A 源码分析（`r<rev>` / `分析 r<rev>`）：先用运维 MCP 的 `e9_svn_log` + `e9_svn_diff` 取变更，再用查询 MCP 的 `search_graph` + `trace_path` 做影响面，产出 `output/r<rev>/` 的 facts、design、reverse_lookup 与报告。
2. 阶段 A+ 功能用例设计（`生成功能测试用例` / `功能用例清单`）：以专业测试人员身份，基于阶段 A 的 `behavior_change` 与影响面，全面设计功能测试用例（增删改查、边界值、等价类、异常、组合、权限与状态），产出 `output/r<rev>/functional_test_cases.md`。**不落任何自动化代码。**
3. 阶段 A++ 人工审核（`审核功能用例`）：提交功能用例清单供人工审核，按反馈反复修改，直至人工确认定稿；**确认后才允许进入阶段 B**。
4. 阶段 B 用例实现（`按方案实现接口自动化`）：按定稿的功能用例清单 + design + reverse_lookup，抽取需自动化条目落接口封装与用例，用例挂 `@pytest.mark.r<rev>`。
5. 前置数据构建（用例依赖环境业务数据时）：读取 `reverse_lookup.json` 生成数据计划，经 `tools/test_data_runner.py` 幂等构建，状态写入 `test_data/<模块名>/`；决策树见 `references/prepare-data.md`。
6. 阶段 C 执行（`复测 r<rev>`）：`runpytest.py -m r<rev> --clean`，产出 Allure 原始结果与带时间戳 HTML。
7. 报告分析（`分析测试报告 r<rev>` 或批次报告）：失败指纹分片归因，回写 Allure 并重建报告。端到端推进时，阶段 C 出现失败或报错用例必须自动衔接本步（运行目录即本次产出的 `report/allure-results`，无需再次确认），失败用例只有回写「AI 分析」附件并重建报告后才算闭环；无失败则回复"无失败用例，无需 AI 分析"。单笔和批次仅在报告元数据中区分 revision/batch_id，不复制报告分析规则。

## 环境初始化

当用户要求初始化、配置环境、第一次使用或修改配置时，代为写入配置，不要求用户编辑文件。

1. 只读读取 `config.json`，绝不在回复中回显原文或秘密。
2. 初始化时每次只收集一个字段：测试环境地址；管理员用户名和密码；需要的普通成员账号数（0 到 5）；每个成员的账号和密码。
3. 未填员工槽位写为 `{"user_name": "", "password": ""}`。配置写入采用临时文件加 `os.replace` 原子替换。
4. 确认 MCP（codebase-memory）可用：检查当前会话是否已配置 `codebase-memory` MCP 服务。如果未配置，告知用户将 MCP 地址 `http://10.20.62.239:9750/mcp` 配入 MCP 配置后新开会话。
5. 安装依赖使用 `pip install -r requirements.txt`。成功后只给脱敏环境摘要。
6. 修改配置时，只展示环境地址、管理员用户名和已配置成员数量，再询问改动字段。

## 快速测试

触发词：`快速测试`。

1. 只读检查 `config.json`。可复用条件是：`base_url` 为合法 `http://` 或 `https://` 地址、管理员用户名和密码均非空、最多五个成员账号且每一组用户名和密码成对存在。
2. CI 环境变量覆盖本地值时，说明本次实际使用 CI 环境变量。
3. 配置完整时，仅输出环境地址、管理员用户名和普通成员数量，并等待用户一次确认。确认前不改配置、不分析、不执行测试。
4. 配置缺失、损坏、用户拒绝复用或要求其他环境时，原样返回下列模板并停止，不能逐项追问：

```text
测试环境地址: XXX
管理员账号: XXX
管理员账号密码: XXX
普通成员一账号: XXX
普通成员一密码: XXX

可按需继续补充最多5个普通成员账号
```

5. 收到填写结果后，校验地址和成对规则；把未提供的 `employee1` 到 `employee5` 清为空字符串；以临时文件加原子替换写入 `config.json`；仅回复脱敏摘要。
6. 然后要求提供一个单笔 revision 或批次 revision 集合，依次执行阶段 A、A+（功能用例设计）、A++（人工审核）、B、C；批次阶段 A 内部先逐笔调用单笔分析 worker，再聚合后进入同一 A+/A++/B/C 流程。阶段 C 结束后出现失败或报错用例时，接着执行「测试报告分析」完成 AI 报错分析回写与报告重建，再向用户汇报；无失败则回复"无失败用例，无需 AI 分析"。

## 版本号输入

单笔入口只接受一个正整数 revision，可带 `r` 前缀；批次入口接受 2–10 个正整数、合法闭区间或显式集合，并要求批次总结说明。两者都拒绝 `HEAD`、负数和零。无法判断用户意图时先按批次模板要求补充 revision 集合与 `batch_message`，不得把多笔输入误判成单笔。

## 分析对象分派：单笔与批次共用流程

先识别分析对象，再选择入口：

1. **单笔**：`分析 r349084`、`Revision r349084`。调用现有 `run_analyse()` / 单 revision worker，产出 `output/r<rev>/`。
2. **批次**：`分析 Revision r349181 到 Revision r349184，提交说明：...` 或显式集合。调用 revision-set resolver，逐笔调用同一个单 revision worker，每笔最多 3 次完整 attempt，成功项不重复；全部完成后生成批次 facts/design/reverse_lookup 和 `aggregate_design`。
3. 批次不能创建第二套 A+/A++/B/C 规则。聚合后的联合影响面必须继续按 `references/functional-case-design.md` 设计功能用例并等待人工定稿；只有完整批次且清单定稿才进入阶段 B。

批次输入、resolver、产物和标记细节见 `references/common-analysis-contract.md` 与 `E9_svn_analyse/docs/五期开发/E9五期需求分析.md`。

## 批次阶段 A：逐笔分析与联合聚合

1. 先解析并校验 revision 集合；闭区间必须由读取 E9 信息 MCP 查询实际提交，显式集合不推断中间 revision。resolver 不完整或不可用时停止，不调用本地 SVN/运维 MCP 代查范围。
2. 对 `analysis_order` 中每笔 revision 调用公共单 revision worker，一次 attempt 覆盖 log、diff、结构查询、反查和单笔 facts/design/reverse_lookup。每笔最多 3 次；记录 `attempts`、关键事实缺失、错误工具和脱敏建议。
3. 将所有成功逐笔结果写入批次子目录，再由聚合器去重文件、符号、端点、影响模块和用例候选，保留 `source_revisions`、冲突和图谱未覆盖证据。
4. 任一 revision 仍缺关键事实时生成部分审计报告并将 `stage_b_gate=false`，不得写入接口代码；全部完成才生成可进入 A+ 的 `aggregate_design`。
5. 批次 A+、A++、B、前置数据、C 和报告分析分别复用本 SKILL 后续章节及公共 references，不另建批次 SKILL。

## 阶段 A：分析单笔提交

触发词：`r349084`、`Revision r349084`、`分析 r349084`。

1. 确认查询 MCP（codebase-memory）与运维 MCP（e9-ops）可用。**所有代码分析仅通过 MCP 完成**，禁止执行本地 SVN 操作、禁止用 Grep/Glob/Read/Bash 查询 E9 代码或提交信息，禁止 `detect_changes`。
2. **阶段 A 第一步**必须取时态（运维 MCP，只读，不要 `confirm`，不要 `e9_sync` / `e9_svn_update`）：
   - `e9_svn_log(revision)` → 作者 / 说明 / paths
   - `e9_svn_diff(revision)` → unified diff
3. 然后才做结构查询（查询 MCP）。现网 **没有** `impact` / `callers`：
   - 图内 `src/**/*.java`：`search_graph(file_pattern=...)` 找种子，再 `trace_path(direction="inbound", depth=3)`
   - `get_code_snippet` 取变更方法源码
   - 图外 JSP/SQL/前端：标注「图谱未覆盖」，不编造符号级影响面
   - 详细查询流程见 `.workbuddy/skills/e9-codebase-memory/SKILL.md` 及其 `references/` 目录
4. 分析产出写入 `E9_svn_analyse/output/r<rev>/` 目录：
   - `facts.json`：变更文件、端点、影响范围等事实
   - `design.json`：行为变更、影响摘要、功能用例、接口用例
   - `reverse_lookup.json`：反查证据包
5. 事实字段如 `changed_files`、`endpoints`、`endpoint_diagnostics`、`existing_api`、`diff_excerpt`、`impact`、`frontend_operations`、`pure_frontend`、`change_layer` 不得改写成未证实结论。
6. 若 `facts.json` 的 `pure_frontend` 为 `true`：已跳过 trace_path 与端点提取。补全界面侧 `behavior_change` 与可选功能用例即可，`api_cases` 必须为空，`impact_summary` 保持「纯前端改动，无接口回归项」。回复报告路径后说明无需实现接口自动化，不要发送或等待 `按方案实现接口自动化`。`.jsp` / `.ftl` / `WEB-INF/**` / 配置模板不算纯前端。
   例外——纯前端契约审视：当 diff 显示前端**改变了对某个既有接口返回数据的消费方式**（典型：取数从「数组下标」改为「map 按 key」、新增/收紧某字段的类型或存在性假设、依赖新数据结构）时，须额外判断该接口的返回契约是否支撑前端新逻辑，并按 `references/pure-frontend-contract.md` 补一条**只读契约回归用例**守护这个前提；纯样式/UI 增删、不依赖接口契约的改动不触发此例外。该例外不改变「纯前端无后端回归项」结论，命中的用例仍挂 `@pytest.mark.r<rev>`，报告结论注明「纯前端改动，仅补依赖接口契约回归」。
7. 含任一后端或模糊文件时按非纯前端处理：补全 `design.json` 的 `behavior_change`、`impact_summary`、按 P0/P1/P2 排列且具备 `id/priority/scene/steps/expected` 的 `functional_cases`、带 `suggested_wrapper` 和 `suggested_test` 的 `api_cases`、以及不扩散的 `unchanged_paths`。保留 `env_assumption` 与 `next_command`。`endpoint_diagnostics.needs_manual_review=true` 时 `api_cases` 必须为空：把诊断候选入口列入回复并请人工复核，不得编造接口入口。
8. 影响范围以本次 diff 修改的符号为中心。被调用公共方法本体未变时，说明不扩散，不能把整棵调用树都列为回归范围。没有 HTTP 入口的纯 JSP 或 SQL 改动仍应给出功能用例，但 `api_cases` 可为空。
9. 运行 `cd E9_svn_analyse; python -m svn_analyse render output/r<rev>`，回复 HTML 路径、变更文件数、影响范围、识别接口数。**非纯前端提交的下一句口令是 `生成功能测试用例`（先经过功能用例设计 + 人工审核定稿，才轮到 `按方案实现接口自动化`）**；纯前端提交则说明无接口回归项。然后停止等待确认。

## 阶段 A+：功能用例设计

触发词：`生成功能测试用例`、`设计功能用例`、`功能用例清单`、`写功能测试用例`。

单笔和批次都必须读取 `references/common-analysis-contract.md`，并以 `references/functional-case-design.md` 作为唯一设计规范；批次输入为聚合后的联合影响面，不能降低覆盖要求。

**前置**：必须先完成阶段 A，`E9_svn_analyse/output/r<rev>/` 下存在 `facts.json` 与 `design.json`；缺失时先补做阶段 A。

1. 读取阶段 A 产出的 `facts.json`（`behavior_change`、`impact`、`changed_files`、`endpoints`、`frontend_operations`）与 `reverse_lookup.json`，确定「本次行为变更点」与「影响面调用方」清单。
2. 严格按 `references/functional-case-design.md` 的方法论，以**专业测试人员**身份设计功能测试用例，全面覆盖：增删改查（CRUD）、边界值、等价类、异常、组合场景、权限与状态流转，以及**场景法（核心主流程）**与**状态转换测试（状态机建模）**（详见该文件「专项一 / 专项二」）。场景法必须先做「影响面透出路径 → 功能模块归并」（见该文件「专项一」第一步）：**列出本次改动透出到的全部受影响功能模块，对每个受影响模块至少设计一条该模块的场景法核心主流程用例**（模块内存在多条子功能透出路径时可多条）；**先覆盖全影响模块（横向），再针对每个模块覆盖全功能（纵向）**，不得只挑入口最好确证的单个模块。核心主流程用例中「覆盖变更行为点最核心、入口最直接」的一条作为本 revision 的**核心主用例（P0）**，其余模块主流程与模块内补充用例围绕它展开。场景法主流程**首步骤禁止为查询类接口**——须按「前置数据准备」规则（见该文件「专项一·前置数据准备」）**先自动分析能否用已有前置接口造数，能造则直接写成具体可执行步骤、最大限度拆解多步链路（创建→关联→配置→触发→校验）；确实造不出的部分才标注人工介入并说明数据内容/来源/原因（增量编写，能写多少写多少）**。不得只做「单接口一条用例」的机械映射，也不得把用例简化成「提供前置 + 接口验证」两步式。
3. 用例字段至少含 `编号/标题/类型/优先级/前置条件/测试步骤/测试数据/预期结果/关联接口/是否需自动化`（模板见该文件「用例字段约定」）。来源可追溯：每条对应 `behavior_change` 的一个行为点或一个影响面调用方；接口信息只来自 facts/reverse_lookup，图谱未覆盖的 JSP/SQL/前端标注「图谱未覆盖」，不编造接口与返回结构。
4. 纯前端提交：仍产出功能用例清单，但 `关联接口` 与 `是否需自动化` 按契约审视结论填写（纯样式/UI 增删 → 全 `manual`；改变接口消费方式 → 命中契约回归的条目标 `contract`）。
5. 产出文件：`E9_svn_analyse/output/r<rev>/functional_test_cases.md`（Markdown 表格）。**本阶段不落任何 `page_api/`、`test_case/` 自动化代码。**
6. 回复清单路径、用例总数、按覆盖维度与优先级的分布，然后进入「阶段 A++ 人工审核」，停止等待人工反馈。**未经人工确认定稿，绝不进入阶段 B。**

## 阶段 A++：人工审核

触发词：`审核功能用例`、`确认功能用例`、`功能用例定稿`。

1. 把已生成的 `functional_test_cases.md` 内容完整呈现（表格 + 关键字段）供人工审核。
2. 等待人工反馈，反馈类型包括：增删用例、修改某条的步骤/预期/数据、调整优先级、补充遗漏场景（如某类边界、某类组合、某角色权限）。
3. 收到反馈后**就地修改** `functional_test_cases.md` 并再次呈现改动点，重复「反馈 → 修改 → 再确认」循环，直到人工明确表示「确认 / 定稿 / 通过 / 可以了」。
4. 人工确认前，若中途收到「换一个 revision」或「回到阶段 A」等指令，按对应触发词重新进入相应阶段，不强行推进。
5. 收到人工定稿确认后：回复「已定稿」并说明下一步口令 `按方案实现接口自动化`，停止等待。**只有在此之后，阶段 B 才被允许执行。**

## 阶段 B：实现接口自动化

触发词：`按方案实现接口自动化`、`实现 r349084 用例`、`实现接口自动化`。

**前置（本次新增）**：进入阶段 B 前，功能用例清单 `functional_test_cases.md` 必须已经人工审核定稿。若尚未定稿，先完成「阶段 A+ 功能用例设计」与「阶段 A++ 人工审核」，不得跳过。

单笔和批次均遵守 `references/common-analysis-contract.md` 的 B 门禁、证据和复用规则；批次额外检查 `batch_status=complete`、`aggregate_design.eligible_for_stage_b=true` 和 `stage_b_gate=pass`。

1. 读取当前 revision 的 `E9_svn_analyse/output/r<rev>/design.json`、`reverse_lookup.json` 与定稿的 `functional_test_cases.md`；不存在时先完成阶段 A。用例依赖业务前置数据时，按 `references/prepare-data.md` 和 `functional-to-api-test/references/test-data-reuse.md` 的决策树，先查询并复用当前环境数据，确认缺失后才进入「前置测试数据构建」，不直接向用户索要内部 ID。**从定稿的功能用例清单中抽取「是否需自动化 ≠ manual」的条目落为接口用例**，每条接口用例在 docstring 中标注来源功能用例编号（如 `FC-3`）；`manual` 条目只作回归指引，不生成 pytest 用例。

   **接口调用链硬性要求（每条接口用例必读）**：接口自动化验证的是「跨接口的前后数据流转」，不是「单接口响应的字段正确性」。因此：
   - 一条接口用例**至少调用 ≥2 个存在数据依赖关系的接口**，前一步返回的业务标识（新建返回的 ID/UUID）必须作为后一步请求的入参，形成「造数 → 读取/处理 → 校验」的真实调用闭环；断言针对**链路最终态与中间关键态**，而不是对同一接口的响应反复断言。
   - **「单接口 + 拆分断言」≠ 多步骤**：只调用一个接口、再用多个 `assert` 拆同一份响应（字段存在性、类型、文案各写一条），本质仍是单接口用例，**禁止**。判定的唯一标准是**实际发起了多少次不同的接口调用**，与写了几条 `assert` 无关——调一个接口写了 5 条断言（如 `api_status`、字段存在、类型正确、文案正确）依旧算单接口。
   - **先凑链路，凑不出再说明**：优先用 `reverse_lookup` 证据里的已有前置接口（新建/保存/提交/导入类）造出前置数据，凑出 ≥2 个接口的链路。确因业务形态无法形成跨接口链路时（纯查询导出、只读契约回归等），必须在 docstring 中写明「无法形成跨接口链路」的客观原因，并把该条归为补充用例（`contract`）而非主用例；不得把「凑不出链路」当默认结果，更不得用拆断言的方式伪装成多步骤。
2. 运行 `cd E9_svn_analyse; python -m svn_analyse inventory` 并读取 `E9_svn_analyse/output/_inventory.json`。URL 已有封装时复用它，只追加测试与 revision mark，不创建重复封装。
3. 新封装位于 `page_api/<模块名>_api/`，继承 `page_api.public.base_api.BaseAPI`；新用例位于 `test_case/test_<模块名>_case/`。不得在封装或用例中硬编码域名或 IP。
4. 新增或复用的测试添加 `@pytest.mark.r<rev>`；保留所有已有 mark。遵循 `docs/api_test_case_spec.md` 的命名、fixture、断言和数据规范。
5. 用例读取环境对象 ID 时，校验要兼容 UUID 十六进制串与数字主键（E9 看板等模块返回 UUID），不要假设 `isdigit`。
6. **返回值断言闭环（本次新增，必做）**：用例写完、断言补齐前，先按以下顺序闭环，禁止凭猜测写死在文档里的返回结构：
   - 在用例中**临时打印真实返回值数据**（用 `print()` 或 `allure.attach`，只打印业务字段，禁止打印账号/密码/cookie/token/完整请求头等敏感信息；脱敏后再打印）；
   - 运行一次 pytest，读取真实返回 JSON 结构；
   - **按真实返回值补充必要的返回值断言**（字段存在性、类型、业务标志、关键提示文案）；
   - 再次执行 pytest 直至闭环通过；
   - **通过后删除临时的返回值打印内容**，只保留最终断言与受管 `allure.attach` 证据，再交付。
7. 更新库存后执行 `python runpytest.py -m r349084 --clean`。回复带时间戳的 Allure 目录；环境 revision 未确认时，按安全前提解释失败。出现失败或报错用例时，先执行「测试报告分析」完成 AI 报错分析回写与报告重建，再把报告路径与分析结论一并回复用户。

## 前置测试数据构建

触发时机：阶段 B 的用例依赖测试环境中的业务数据（组件 ID、文档 ID、流程实例、过滤配置等）。原则是优先自动构建，而不是向用户要现成 ID——用户通常也不掌握这些内部标识。r349149 看板、r349155 文档、r349152 表单建模是该模式的三个已落地实践；完整决策树与四类异常处理见 `references/prepare-data.md`。

1. 读取 `output/r<rev>/reverse_lookup.json`：入口端点、调用链、参数契约（`contracts`）、前端操作证据（`frontend_operations` / `frontend_scan.misses`）与覆盖一致性。证据缺口按决策树分别处理：端点为空（`needs_manual_review=true`）阻塞并给出候选；参数不明或前端 miss 时降低置信度、协议层断言先行；纯前端或无接口变更不触发数据构建。
2. 生成或复用数据计划：已有 `test_data/<模块名>/<模块名>_data_plan.json` 时直接复用；缺失时按 reverse_lookup 的链路写「查询 A → 创建 B → 配置 C → 验证 D」计划（schema 与校验见 `tools/test_data_runner.py`），并实现/复用 `tools/prepare_<模块名>_test_data.py`，在运行器 `MODULE_REGISTRY` 登记。
3. 构建与复用一律走运行器：`python -m tools.test_data_runner status --module <模块名>` 判定就绪；`build` 幂等构建（已有基线自动复用，受管字段与敏感门禁自动注入）；`cleanup` 仅按状态文件回收。构建失败必须给出可操作阻塞：失败的计划步骤、对应端点与建议动作，不得转为向用户索要内部 ID。
4. 构建状态写入 `test_data/<模块名>/<模块名>_test_data.json`（Git 管理、按模块分类）；用例读取顺序为环境变量优先、数据基线文件兜底，保证克隆仓库后无需手工配置即可执行。不要把用例数据放 `runtime/`。
5. 把"环境部署探测"并入准备流程：对行为变更点做同一查询的变更前后对比，结论写入状态文件（如 `env_deployed_fixed`）。结果呈修复前特征时明确记录"环境尚未部署 r<rev>"，P0 断言采用结构化口径（见阶段 C），行为差异留信息性证据。
6. 参数编码是私有格式时（如 E9 `DecryptLZ` 的 LZW 逗号码值），在封装内实现纯 Python 编解码，并用 1:1 复刻服务端解码器的离线测试验证互逆；不要引入格式不匹配的第三方库。
7. 探测候选字段遇到类型不适用（CLOB/LOB 触发 SQL 错误）或无数据时排除并换下一个；全部候选失败则如实报告，请用户指定数据模型或人工提供。

## 阶段 C：复测

触发词：`复测 r349084`、`执行测试 r349084`、`跑用例 r349084`。

执行 `python runpytest.py -m r349084 --clean`。阶段 C 不重新分析提交或无理由修改业务测试；若用户要求全部回归，执行 `python runpytest.py`。执行结束后出现失败或报错用例时，自动衔接「测试报告分析」（运行目录即本次产出的 `report/allure-results`）；无失败则回复"无失败用例，无需 AI 分析"。

批次阶段 C 仅将 marker 扩展为任一关联 revision mark 或经校验的 OR 表达式，并写入 `batch_id`、`analysis_run_id` 和实际表达式；清理、环境版本假设、Allure 和失败报告分析仍完全复用公共契约。

断言策略（环境部署版本未确认时）：P0 行为口径用例以结构化断言为通过标准——成功标志（如 `api_status`）加数据载荷存在；行为级证据（空值组是否包含、行数对比等）用 `allure.attach` 记录为信息性附件，供环境部署后复核差异。这样环境落后于工作副本时不会误报失败，部署后同一套数据重跑即可验证行为变化。依赖环境数据标识的用例在数据缺失或格式无效时安全跳过（`pytest.skip`），跳过不构成验收通过。

## 库存、覆盖校验与用例选取

- 用户要求接口覆盖校验时，运行现有库存或覆盖工具，报告 URL 是否已封装、已有测试与缺口；已存在的 URL 必须复用。
- 用户说"等保分保相关用例""按功能关键词选用例"等内容时，先运行 `cd E9_svn_analyse; python -m svn_analyse select --keyword 等保分保`。只选择查询结果中的用例；确认清单后执行 `python runpytest.py -m r349094 --clean`，不得把相邻 revision 自动混入。
- 用户说"r349094 有没有用例覆盖"等内容时，先运行 `cd E9_svn_analyse; python -m svn_analyse select --revision r349094`。再读取当前 revision 的 `facts.json` 受影响符号，并在 MCP 可用时执行 `cd E9_svn_analyse; python -m svn_analyse check-consistency --revision r349094`；输出 mark 关联与 callers 反查的覆盖情况和差异原因。
- 用户按其他 revision 选例时，同样只选择保留相应 `@pytest.mark.r<rev>` 的测试。查询没有返回用例时，明确说明当前库存没有对应自动化用例，不得把无关测试补入执行集。

## 测试报告分析

触发词：`分析测试报告 r349084`、`测试报告有失败用例`、`看看测试报告里报错`、`分析一下原因`、`帮我分析`。

1. 只分析用户明确指定或已确认的一次运行目录；由本流程阶段 B/阶段 C 执行后直接衔接时，运行目录就是刚产出结果的 `report/allure-results`，无需再次确认。未指定时列出最近运行目录，等待确认；不得把历史 `allure-results` 混入。
2. 读取 `references/allure-analysis.md`。冻结所有 `*-result.json` 中 `failed` 和 `broken` 记录到运行专属 manifest。每条记录仅含绝对路径、UUID、SHA-256、状态和脱敏截断错误；以规范化失败指纹去重。
3. 敏感信息不得进入 manifest、子任务输入或附件：账号、密码、cookie、token、完整请求头、完整响应体。无失败时直接回复"无失败用例，无需 AI 分析"，不进行分片。
4. 对唯一失败指纹按 `min(10, 唯一失败指纹数, 可用并发数)` 分片。每个分析任务只读分配的不可变 JSON，不能读取配置、执行命令、改文件或访问网络。每个指纹只输出：

```json
{
  "fingerprint": "manifest 中的值",
  "category": "environment|credentials_config|dependency|test_data|test_code|product_defect|unknown",
  "conclusion": "不含敏感信息的结论",
  "evidence": "来自脱敏错误的简短证据",
  "recommendation": "下一步操作",
  "confidence": 0.0,
  "environment_revision_assumption": "测试环境部署版本尚未确认",
  "needs_human": true
}
```

5. 主会话是唯一写者。校验指纹白名单、类别、字段长度、置信度、敏感信息和结果 SHA-256；哈希变化即标为过期且不回写。
6. 每个结果 JSON 只保留一个受管 `AI 分析` attachment，正文路径为 `ai-analysis-<result-uuid>.txt`。保留原 `status`、`statusDetails`、`description` 和原附件；使用临时文件加 `os.replace` 原子替换；重复分析替换而非累加。
7. 写入不含长堆栈的 `ai-analysis-summary.json`。固定顺序为 `pytest -> manifest -> analysis -> validation/writeback -> allure generate -> summary`。回写后生成新的带时间戳 Allure HTML 目录；Allure CLI 不可用时交付回写结果并说明。
8. 回复总数、通过数、失败数、唯一失败类型数、每类通俗原因和可操作建议，并先说明环境 revision 假设。无已确认部署证据时，不把断言失败归为产品缺陷。

## Allure 报告查看（交付收尾）

阶段 C 与报告分析产出 Allure HTML 后，交付时必须让报告能被真实打开。Allure 是前端 SPA，`file://` 直接打开时点击「类别 / 测试套 / 包」会因浏览器拦截 `data/*.json` 的异步请求而 404。因此交付时按下面步骤起本地 HTTP 服务，再用 http 链接打开（或交付 http 链接给用户）：

1. 在 `report/` 目录起静态服务（cwd 必须在报告目录或其上层）：

```powershell
cd api-test-E9/report
python -m http.server 8917 --bind 127.0.0.1
```

2. 用 http 访问，例如 `http://127.0.0.1:8917/allure-report-r349137/index.html`，并以该 http 链接作为交付/预览入口，不得给 `file://` 路径。
3. 说明：不要用浏览器直接打开 `index.html`（file:// 下点 Categories 会 404）；如需离线查看可 `allure open <报告目录>`，但同样走本地服务而非 file 协议。
4. 沙箱注意：Git Bash 下 `allure`（bash 包装脚本）fork 易因资源不足失败，改用 PowerShell 调 `allure.bat` 生成报告；生成 HTML 后服务端口若被占用换一个空闲端口即可。

## 全流程可观测性（四期 T4.6）

阶段 A/B/C、MCP 查询、源码反查、数据构建、pytest、清理都要留阶段 span，报告才能按阶段还原墙钟时间：

- 阶段 A 由分析 CLI 自动采集（`stage_a` / `mcp_query` / `reverse_lookup` 三个 span，失败记 error_type）；
- 阶段 B、阶段 C、数据构建与清理在各自边界用 `tools/phase_trace.py` 的 `begin` / `end` 记录；失败必须带 `--error-type`；
- 报告区分**确证耗时**（实际采集）与**估算耗时**（相邻 span 空档推断），估算只用于还原时间轴，不作为效率结论；
- trace 只记录阶段、步骤、耗时、状态与错误类型；不采集凭据、Cookie、完整请求头/响应体。产物在 `runtime/trace/`，不入 Git；`E9_TRACE=0` 可关闭采集。

```powershell
python -m tools.phase_trace begin --revision r349084 --phase stage_b --step implement
python -m tools.phase_trace end --revision r349084 --span-id sp-0004
python -m tools.phase_trace report --revision r349084
```

## Git 交付

提交前运行：

```powershell
python .workbuddy/skills/svn-impact/evals/git_readiness_check.py --repo-root .
```

通过后询问用户是否提交。获得确认后，在本仓库中仅暂存 `page_api/`、`test_case/`、`tools/`、`docs/`、`.workbuddy/`、`skill_utils/`、`test_data/`、`config.json`、`E9_svn_analyse/`（测试环境凭据文件按三期变更允许提交团队内部 GitLab）与必要的仓库元文件，再以 `test: <范围>` 提交并推送。不要使用宽泛的 `git add .`；工作区存在他人暂存的变更时，用路径限定提交（`git commit -- <路径>`）只提交本次范围。

远端地址需要用户提供。收到地址后运行 `git remote add origin <地址>`（或安全地更新已有 origin），再 `git push -u origin <当前分支>`（本仓库默认分支为 `master`）。远端交付必须可见 `.workbuddy/skills/`、`page_api/`、`test_case/`，且不包含敏感或运行时产物。

## MCP 服务边界

- E9 源码图谱不在本仓库中。所有代码分析统一走外部 MCP（codebase-memory），**绝对禁止**本地图谱查询、本地 SVN 操作、或使用 Grep/Glob/Read/Bash 查询 E9 代码。参见上方"E9 代码查询硬性禁令"。
- 图谱运维（SVN 同步、索引重建、状态查看）由独立的 **codebase-memory-ops** MCP（`e9-ops`）提供，端点 `http://10.20.62.239:9750/servers/e9-ops/mcp`。写入操作需传 `confirm="e9-sync"`。详细工具说明见 `.workbuddy/skills/e9-codebase-memory/SKILL.md` 的"运维 MCP"章节。
- 接口自动化未获明确请求时不初始化图谱，库存扫描是默认方式。
- 现网查询 MCP **没有** `impact` / `callers`；结构查询用 `search_graph` + `trace_path`。时态查询用运维 MCP 的 `e9_svn_log` / `e9_svn_diff`。企业 HTTPS 网关（R1）仍按远端计划，不阻塞这两类现网工具。绝不暴露 shell、任意路径、SVN URL 或凭据参数。
- 刷新为异步受控作业：仓库锁定、SVN 更新、图谱增量同步、revision 校验、原子激活。
- **E9 代码查询仅能使用 codebase-memory MCP**：禁止用 Grep/Glob/Read/Bash 等任何本地工具查询 E9 代码或提交信息。详细规范见 `.workbuddy/skills/e9-codebase-memory/SKILL.md`。

## 命令参考

```powershell
cd E9_svn_analyse; python -m svn_analyse inventory
cd E9_svn_analyse; python -m svn_analyse reverse-lookup r349084
cd E9_svn_analyse; python -m svn_analyse reverse-lookup r349084 --symbol FuncService
cd E9_svn_analyse; python -m svn_analyse render output/r349084
python runpytest.py -m r349084 --clean
python runpytest.py
python -m tools.test_data_runner list
python -m tools.test_data_runner status --module board
python -m tools.test_data_runner build --module board
python -m tools.test_data_runner cleanup --module board
```

报告分析工具必须以模块方式调用（直接运行脚本会因绝对包导入失败）：

```powershell
python -m tools.allure_ai_analysis freeze --run-dir report/allure-results
python -m tools.allure_ai_analysis writeback --run-dir report/allure-results --manifest report/allure-results/ai-analysis-manifest.json --analysis <分析结果JSON>
python -m tools.allure_ai_analysis rebuild --run-dir report/allure-results
```

## 进度记录

进度记录位置按分期（三期起位于 `E9_svn_analyse/docs/`）：一期 T1.x → `E9_svn_analyse/docs/一期开发/开发进度日志.md`；二期 T2.x → `E9_svn_analyse/docs/二期开发/二期开发进度.md`；三期 T3.x → `E9_svn_analyse/docs/三期开发/三期开发进度.md`；四期 T4.x → `E9_svn_analyse/docs/四期开发/四期开发进度.md`；远端开发 R.x → `E9_svn_analyse/docs/远端开发/远端开发进度.md`。完成计划任务或遇到阻塞时，向对应文件追加：任务编号和名称、状态、开始/完成时间、相对交付路径、逐项验收结果、偏差或问题以及下一步。记录中不能出现秘密。
