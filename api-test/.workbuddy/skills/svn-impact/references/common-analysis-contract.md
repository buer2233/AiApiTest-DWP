# 单笔与批次共用分析契约

本文件是 `svn-impact` 的公共规则。单笔 revision 和批次 revision 集合都必须引用本契约；批次不得复制或弱化其中的 MCP、安全、证据、功能用例、阶段门禁、数据准备、执行和报告规则。

## 1. 统一生命周期

两种分析都遵循同一条业务链：

```text
输入解析 → 阶段 A 事实与影响分析 → 阶段 A+ 功能用例设计
→ 阶段 A++ 人工审核定稿 → 阶段 B 接口用例实现
→ 前置数据准备（如需要）→ 阶段 C pytest/Allure
→ 失败报告分析与报告交付
```

批次只在阶段 A 增加两个编排动作：

```text
解析 revision 集合 → 逐 revision 调用单笔分析 worker（可重试）
→ 汇总 facts/design/reverse_lookup → 形成 aggregate_design
```

批次聚合完成后，仍必须按本文件的 A+、A++、B、C 顺序推进。不能因为存在 `aggregate_design` 而跳过功能用例设计或人工审核。

## 2. 输入与输出上下文

| 项目 | 单笔 | 批次 |
|---|---|---|
| 输入 | 一个正整数 revision | 2–10 个 revision，或闭区间解析出的 2–10 个实际 revision，加 `batch_message` |
| 阶段 A 单元 | 一个 revision worker | 多次调用同一个 revision worker；每笔最多 3 次完整 attempt |
| 事实产物 | `output/r<rev>/facts.json` | `output/batch_.../revisions/r<rev>/facts.json`，再生成批次 `facts.json` |
| 设计产物 | `design.json` | 逐笔 `design.json` + 批次 `aggregate_design` |
| 用例清单 | `functional_test_cases.md` | 批次级 `functional_test_cases.md`，来源保留 `source_revisions` |
| 执行选择 | `r<rev>` mark | 任一关联 `r<rev>` mark，或经校验的 OR 表达式 |
| 追踪元数据 | `revision`、mark | `batch_id`、`analysis_run_id`、revision 集合、实际 marker 表达式 |

## 3. 必须复用的规则与实现

### 3.1 MCP 与证据边界

- E9 SVN log/diff 通过运维 MCP；E9 源码、符号、调用链和端点证据通过查询 MCP。
- 禁止本地 SVN、读取 E9 源码、图谱 CLI、未授权 HTTP 查询和凭猜测补齐事实。
- 先取时态事实，再做结构查询；图谱未覆盖的 JSP/SQL/前端必须明确标记，不编造符号、URL、参数或返回结构。
- 每个结论保留证据来源、置信度、未覆盖路径和环境版本假设。

### 3.2 阶段 A 事实字段

单笔 worker 和批次逐笔产物沿用同一事实字段：`changed_files`、`symbols`、`endpoints`、`endpoint_diagnostics`、`existing_api`、`impact`、`frontend_operations`、`pure_frontend`、`change_layer`、`warnings`、`confidence`、`diff_excerpt`。批次只在外层增加 provenance、attempt、来源 revision 和跨提交摘要。

### 3.3 功能用例设计

统一读取 `references/functional-case-design.md`。该文件中的覆盖维度、影响模块归并、场景法、状态转换、前置数据自动分析、用例字段、证据边界和人工审核要求，对单笔和批次完全相同。批次必须先把所有逐笔影响面合并去重，再按同一规范覆盖全部联合影响模块；每条用例保留 `source_revisions`。

### 3.4 阶段 B 与前置数据

- 阶段 B 只消费完整且已人工定稿的设计；端点诊断需要人工复核时阻断。
- URL 已封装则复用，不能重复创建；新增测试从定稿功能用例中抽取，并保留功能用例编号。
- 用例依赖业务对象时统一遵守 `references/prepare-data.md`，优先自动造数、幂等复用、状态文件只保存业务标识。
- 单笔测试追加一个 revision mark；批次测试在同一测试上追加全部关联 revision mark，保留已有 marks。

### 3.5 阶段 C、Allure 与报告分析

单笔和批次都使用同一 runner、清理策略、环境版本假设、Allure 结果目录、失败指纹分析和受管附件回写规则。批次只额外写入 `batch_id`、`analysis_run_id`、revision 集合和 marker 表达式；失败归因仍按 `references/allure-analysis.md` 执行。

## 4. 代码复用边界

阶段五不得复制一份“单笔分析实现”。应抽取或保持以下公共函数/模块，由单笔入口和批次编排器共同调用：

| 公共能力 | 当前实现/目标抽象 | 批次调用方式 |
|---|---|---|
| revision 标准化 | `revision.parse_revision`、`revision.revision_mark` | resolver 输出逐笔 revision 后复用 |
| 时态查询 | `cli._fetch_temporal`、`mcp_client.svn_log/svn_diff` | 每个 attempt 调用一次完整 worker |
| 变更事实 | `facts.py` 的文件、符号、端点和诊断函数 | 逐笔原样产出，外层聚合 |
| 结构/前端反查 | `cli._collect_graph`、`reverse_lookup.build_reverse_lookup` | 每笔独立取证，聚合只合并证据 |
| 库存与覆盖 | `inventory.py`、`coverage.py`、`revision_meta.py` | 设计前统一读取，批次按 revision 集合追踪 |
| design 骨架与报告 | `report.design_skeleton`、`report.write_outputs`、`report.render_*` | 单笔直接写；批次复用渲染器并增加批次上下文 |
| 执行与报告 | `runpytest.py`、Allure 分析工具、阶段 trace | 只扩展 marker 表达式和批次元数据，不复制失败分析逻辑 |

推荐代码分层：

```text
revision.py              单笔 revision 原子规则
revision_set.py          批次输入和 resolver（新增）
analysis_worker.py       单 revision facts/design/reverse_lookup worker（抽取）
batch_orchestrator.py    逐笔调度、3 次 attempt、聚合和门禁（新增）
report.py / inventory.py / coverage.py / runner
                         单笔与批次共同调用
```

`run_analyse()` 保持单笔 CLI 兼容；其内部应委托 `analysis_worker.py`，批次编排器也只能调用该 worker，不得复制 `_run_analyse_inner` 的查询和事实逻辑。

## 5. 复用验收

- 单笔和批次的功能用例设计均明确引用 `references/functional-case-design.md`，不出现分叉规则。
- 单笔回归测试和批次测试使用同一 MCP 禁令、证据字段、前置数据、Allure 和报告分析规则。
- 批次测试至少验证：逐笔 worker 被调用、成功 revision 不重复、失败 attempt 最多 3 次、聚合保留来源 revision，阶段 B 只消费完整且已定稿批次。
