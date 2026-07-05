# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 需求说明书

## 元信息 [必填]

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 |
| 父需求 | 环境与模块通过率页面（`project-info/demand/环境与模块通过率页面-需求说明.md` v0.3 已冻结） |
| 阶段拆分 | 基于 `project-info/demand/环境与模块通过率页面-阶段拆分计划.md` P4/P5 调整：本阶段先交付 Jenkins 三条流水线脚本，前后端实际 Jenkins 执行对接后置到下一阶段。 |
| 需求分级 | M |
| 裁剪说明 | 不裁剪需求分析、功能测试用例、Jenkins 脚本 TDD、独立审查、RTM、验收包、commit 和 push。本阶段按主人 2026-07-05 裁决，不开发前端/后端实际 Jenkins 执行对接，因此前端页面实现与 DRF 任务触发接口作为后续阶段范围；本阶段 UI 产物调整为 Jenkins Job 参数界面与人工验收交互说明。 |
| 关联模块 | `jenkins` / `api-test` / `docker`；`back-end`、`front-end` 本阶段只保留后续契约说明，不做执行对接代码。 |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |
| 依赖 | P1 用户权限底座、P2 测试数据底座与只读通过率页面、P3 用例详情状态审计与趋势数据已交付。 |

---

## §0 待澄清清单（澄清门禁）[必填]

> 主人 2026-07-05 已逐条确认原 Q1-Q10，并对 Q2、Q7、Q9 做出范围调整：本阶段接入实际 Jenkins 流水线脚本，但前后端执行对接后置；Jenkins 和 Allure 直接跳转不额外加平台 Cookie 验证。主人已确认“全部采纳推荐”，Q11 按推荐方案 A 冻结。

| 编号 | 待澄清点 | 可选方案 / 影响面 | 推荐裁决 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Q1 | P4 新模型归属 | 原推荐：未来前后端接入时，`jenkins_task`、`module_execution_lock` 继续放在 `metrics` app。 | 继续采纳原推荐；本阶段不建表，后续接入阶段沿用该归属。 | 确认 | 已确认 |
| Q2 | 本阶段 Jenkins 开发策略 | 原推荐为后端抽象取消服务；主人改为本阶段先写实际 Jenkins 流水线脚本，前后端执行对接后置。 | 本阶段交付 3 条 Jenkins Pipeline 脚本并支持主人直接在 Jenkins 上验收；DRF/Vue 触发、取消和同步留下一阶段。 | 本阶段需要接入实际 Jenkins 任务，重新开发 3 条 Jenkins 流水线脚本。 | 已确认 |
| Q3 | P4 演示/配置数据来源 | 原推荐扩展 `seed_demo_metrics`；本阶段不做前后端数据演示。 | 本阶段不扩展 seed；Jenkins 人工验收使用 Jenkins Job 参数。后续前后端接入时再扩展 seed 或同步数据。 | 确认 | 已确认 |
| Q4 | Jenkins/Allure 链接来源与安全策略 | 原推荐外链由后端返回；本阶段直接在 Jenkins 验收。 | Jenkins 和 Allure 页面直接跳转访问，不叠加平台 Cookie 验证；后续平台侧只保存/展示链接。 | 确认 | 已确认 |
| Q5 | 取消任务权限 | 原推荐管理人员或任务触发人可取消。 | 后续平台接入阶段沿用；本阶段 Jenkins 权限由 Jenkins 自身账号/Job 权限控制。 | 确认 | 已确认 |
| Q6 | 取消状态和锁释放时机 | 原推荐取消后进入 `canceling` 并释放锁。 | 后续平台接入阶段沿用；本阶段流水线脚本不维护平台锁表。 | 确认 | 已确认 |
| Q7 | 模块行 Jenkins 任务入口开放规则 | 原推荐 P4 打开 `jenkins_tasks=true`。主人调整为本阶段不做前后端实际执行对接。 | 本阶段不改前后端按钮行为；下一阶段再开放模块行 Jenkins 任务、失败重试和模块重试入口。 | 前后端暂不开发实际 Jenkins 执行对接，Jenkins 流水线脚本先写出来配置并在 Jenkins 上测试。 | 已确认 |
| Q8 | 今日任务日期口径 | 原推荐按后端 `timezone.localdate()`。 | 后续平台接入阶段沿用；本阶段 Jenkins cron 按 Jenkins controller 时区执行。 | 确认 | 已确认 |
| Q9 | 平台 Cookie 验证与外链访问 | 原推荐区分 Jenkins 内部 API 地址与公开跳转地址。主人补充外链不单独限制。 | 只有平台 DRF API 需要 Cookie 验证；Jenkins 页面和 Allure 报告直接跳转访问，不追加平台鉴权。 | 只有平台接口需要 Cookie 验证，直接跳转 Jenkins 和 Allure 报告不单独做限制。 | 已确认 |
| Q10 | Allure 报告入口来源 | 原推荐先使用任务记录中的 `allure_report_url`。 | 本阶段由 Jenkins Pipeline 归档并尝试发布 Allure；下一阶段平台保存 Jenkins/Allure 可访问链接。 | 确认 | 已确认 |
| Q11 | 每日全量“一个模块一个执行 job”的 Jenkins Job 组织方式 | 方案 A：每个模块在 Jenkins 配置一个独立 Pipeline Job，均加载脚本 1，并各自设置 `CASE_PATH`，每个 Job 都配置凌晨 2 点 cron；方案 B：一个 orchestrator Job 在凌晨 2 点读取模块清单并并行触发每个模块的 downstream Job；方案 C：一个 Job 内用多个 stage 顺序/并行执行所有模块。影响脚本复杂度、Jenkins 配置量和后续平台任务记录粒度。 | 采用方案 A：最贴合“一个模块一个执行 job”，实现最稳，后续平台可按 module/job_name 建立任务映射；当前模块数少，配置成本可控。 | 采纳推荐方案 A：每个模块一个独立 Pipeline Job，均加载脚本 1，分别配置 `CASE_PATH` 和 `0 2 * * *` cron。 | 已确认 |

---

## §1 需求背景与目标 [必填]

- **背景**：P1-P3 已完成平台登录、基础测试数据、模块通过率、用例详情、状态审计和趋势数据。下一步需要把 Jenkins 执行主干先落到可运行脚本，使主人可以直接在 Jenkins 上验证每日全量、失败重试和模块重试三类任务，再进入后续前后端执行对接阶段。
- **目标**：
  - 交付 3 条 Jenkins Pipeline 脚本：每日全量模块执行、失败重试、模块重试。
  - 每日全量脚本支持按模块配置独立 Jenkins Job，并在每天凌晨 2 点执行该模块全部用例。
  - 失败重试脚本支持“勾选失败用例”和“一键失败重试”两种入口共用同一执行方式：传入当前模块失败用例 node id 列表执行。
  - 模块重试脚本支持用户后续点击“模块重试”后执行当前模块全部用例。
  - 三条脚本均复用 `api-test/tools/ci_runner.py`，不在 Groovy 中复制 pytest、失败 node id 收集或 Allure 生成规则。
  - 三条脚本均兼容 Windows/Linux Jenkins agent，归档 `api-test/runtime/ci-runs/<run_id>/` 运行产物，并尝试发布 Allure。
- **成功指标 / 价值**：
  - 主人可在 Jenkins 中手工创建/配置三类 Job 并完成验收。
  - 产物结构稳定，后续后端可以直接读取或同步 summary、failed node ids、Allure 结果和报告链接。
  - 明确每日全量/模块重试会更新模块“日期”和“执行时间”，失败重试不会更新这两个字段，为后续平台同步规则打底。

## §2 范围 [必填]

- **做（in scope）**：
  - 新增或重构 Jenkins Groovy Pipeline 脚本，形成三条明确脚本：
    - 脚本 1：每日凌晨 2 点模块全量执行脚本。
    - 脚本 2：失败重试脚本，支持选取用例失败重试和一键失败重试共用。
    - 脚本 3：模块重试脚本。
  - 保留一个共享 Pipeline 工具脚本，统一跨平台命令、Python venv、`ci_runner` 调用、Allure 校验、产物归档和 Allure 发布逻辑。
  - 更新 Jenkins 静态测试，先写 RED，再实现脚本，再 GREEN。
  - 更新 `jenkins/README.md`，说明 3 个 Jenkins Job 的创建方式、参数、触发方式、日期/执行时间更新语义和验收步骤。
  - 如新增非敏感 Jenkins Job 名、默认模块路径、运行入口变量，需同步 `.env.example`、Docker 部署文档和静态测试。
  - 保留 `api-test/tools/ci_runner.py` 为执行核心；如发现现有 runner 参数不足，按 TDD 最小扩展并补充 api-test 测试。
- **不做（out of scope）**：
  - 不开发 DRF 触发 Jenkins 的接口，不开发 Jenkins 任务记录表、执行锁表、取消任务接口或结果同步接口。
  - 不开发 Vue 前端的 Jenkins 任务弹窗、失败重试按钮启用、模块重试按钮启用或报告入口展示。
  - 不在本阶段实现平台 Cookie 对 Jenkins/Allure 外链的二次限制。
  - 不把真实 Jenkins 用户名、API Token、Cookie、生产 URL、Jenkins 初始密码或 Allure HTML 产物提交到仓库。
  - 不修改 `api-test` 的业务用例内容。

## §3 用户角色与权限矩阵 [必填]

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| Jenkins 管理人员 / 主人 | 在 Jenkins 上创建和配置三类 Pipeline Job；手工触发失败重试/模块重试；查看 Jenkins 构建和 Allure 报告 | 不把真实凭据写入仓库；不把运行产物提交 git | Jenkins job、build、artifact、Allure 报告 |
| 平台管理人员（后续阶段） | 后续通过平台触发失败重试、模块重试和查看任务/报告 | 本阶段平台按钮仍不触发 Jenkins | 后续由 DRF 返回任务和报告入口 |
| 平台普通成员（后续阶段） | 后续查看任务和报告入口 | 本阶段不做前端执行入口 | 后续由平台权限控制 |

---

## §4 功能清单与验收标准 [必填 · 核心章节]

### F2 每日凌晨 2 点模块全量执行脚本

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 每个模块对应一个 Jenkins Pipeline Job，该 Job 加载“每日全量模块执行脚本”。
  - Job 通过 per-job 环境变量 `JENKINS_MODULE_CASE_PATH` 提供当前模块 `CASE_PATH` 默认值；未配置且未手工填写 `CASE_PATH` 时构建必须失败，避免 cron 跑到示例模块。
  - Job 配置 `0 2 * * *` 定时触发，执行当前模块全部用例。
  - 执行模式传给 `ci_runner` 时使用 `RETRY_MODE=none`。
  - 该执行类型在后续平台同步时会更新模块“日期”和“执行时间”。
- **关联数据表**：本阶段不落库；后续接入阶段关联 `test_run`、`module_snapshot`、`module_run_history`、`jenkins_task`
- **验收标准**：
  - `AC-JENKINS-1.1` — Given Jenkins 已为某模块配置每日全量 Job When 到达每天 02:00 Then Jenkins 自动执行该模块全部用例。
  - `AC-JENKINS-1.2` — Given 主人手工触发每日全量 Job When 构建完成 Then 运行目录包含 `summary.json`、`failed_nodeids.json`、`console.log`、`allure-results` 和 `allure-report`。
  - `AC-JENKINS-1.3` — Given 每日全量执行完成 When 查看 Jenkins 归档产物 Then 对应 runtime 目录被归档，并可通过 Jenkins artifact 或 Allure 插件查看报告。
  - `AC-JENKINS-1.4` — Given 后续平台同步每日全量结果 When 更新模块快照 Then 应更新模块“日期”和“执行时间”字段。

### F6 失败重试脚本

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 失败重试脚本按模块执行，接收 `CASE_PATH` 和 `PYTEST_NODE_IDS`。
  - 用户勾选失败用例后点击“失败重试”和用户点击“一键失败重试”，后续平台都调用同一个后端接口；该接口最终都把目标失败用例 node id 列表传给同一条 Jenkins 失败重试脚本。
  - “一键失败重试”只是快速选择当前模块全部失败用例，不是另一条 Jenkins 执行链路。
  - 脚本使用 `RETRY_MODE=selected` 执行传入 node id；不依赖 Jenkins workspace 中 `.pytest_cache` 推断平台当前失败用例。
  - 失败重试执行完成后，后续平台同步可更新失败用例状态、失败数和通过率，但不会更新模块“日期”和“执行时间”字段。
- **关联数据表**：本阶段不落库；后续接入阶段关联 `test_case_result`、`module_snapshot`、`jenkins_task`
- **验收标准**：
  - `AC-JENKINS-2.1` — Given Jenkins 失败重试 Job 收到一个或多个 pytest node id When 执行构建 Then 只运行这些 node id 对应的用例。
  - `AC-JENKINS-2.2` — Given 未传入任何 node id When 执行失败重试 Job Then 构建应明确失败或中止，并提示必须提供失败用例 node id。
  - `AC-JENKINS-2.3` — Given 失败重试执行完成 When 查看归档产物 Then 运行目录包含 summary、failed node ids、console log 和 Allure 产物。
  - `AC-JENKINS-2.4` — Given 后续平台同步失败重试结果 When 更新模块数据 Then 不更新模块“日期”和“执行时间”字段。

### F7 模块重试脚本

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 模块重试脚本按模块执行，接收 `CASE_PATH`、模块名称和运行标识。
  - 用户后续在前端点击“模块重试”后，后端会触发此脚本执行当前模块全部用例。
  - 脚本使用 `RETRY_MODE=module`，目标为当前模块 `CASE_PATH`。
  - 模块重试执行完成后，后续平台同步会更新模块“日期”和“执行时间”字段。
- **关联数据表**：本阶段不落库；后续接入阶段关联 `test_run`、`module_snapshot`、`module_run_history`、`jenkins_task`
- **验收标准**：
  - `AC-JENKINS-3.1` — Given Jenkins 模块重试 Job 收到模块 `CASE_PATH` When 执行构建 Then 运行该模块全部用例。
  - `AC-JENKINS-3.2` — Given 模块重试执行完成 When 查看归档产物 Then 运行目录包含 summary、failed node ids、console log 和 Allure 产物。
  - `AC-JENKINS-3.3` — Given 后续平台同步模块重试结果 When 更新模块快照 Then 应更新模块“日期”和“执行时间”字段。

---

## §5 状态机定义 [必填]

### 实体：Jenkins Pipeline 执行类型

| 执行类型 | Jenkins 脚本 | ci_runner 参数 | 用例范围 | 后续是否更新模块日期/执行时间 |
| --- | --- | --- | --- | --- |
| 每日全量 | `daily-full-module` | `RETRY_MODE=none` + `CASE_PATH` | 当前模块全部用例 | 是 |
| 失败重试 | `failed-rerun` | `RETRY_MODE=selected` + `PYTEST_NODE_IDS` | 传入的失败用例 node id | 否 |
| 模块重试 | `module-rerun` | `RETRY_MODE=module` + `CASE_PATH` | 当前模块全部用例 | 是 |

### 实体：Jenkins 构建结果

| Jenkins 构建状态 | 触发条件 | 本阶段处理 |
| --- | --- | --- |
| success | `ci_runner` 成功写出 summary 且 Allure HTML 生成成功 | 归档 runtime 产物，Allure 插件可用时发布 |
| unstable / test_failed | 用例失败但基础设施正常 | `ci_runner` 返回 0 并在 summary 标记测试失败；后续平台按 summary 同步 |
| failure | Python 环境、依赖安装、runner、Allure 生成或参数校验失败 | Jenkins 构建失败，人工从 console log 排查 |

---

## §6 数据表设计 [必填]

本阶段不新增数据库表，不执行 Django migration。后续前后端接入阶段仍按已确认方向新增：

- `jenkins_task`
- `module_execution_lock`

两张表继续归属 `metrics` app，并用于记录 Jenkins job/build、任务状态、报告链接、执行互斥和取消状态流转。

---

## §7 Jenkins 脚本契约 [必填 · 冻结后 Jenkins 配置依据]

### 脚本 1：每日全量模块执行

- **建议脚本文件**：`jenkins/scripts/daily-full-module-pipeline.groovy`
- **建议 Jenkinsfile**：`jenkins/Jenkinsfile.daily-full-module`
- **触发方式**：`cron('0 2 * * *')`，也支持人工 Build Now。
- **关键参数**：

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `CASE_PATH` | 是 | 当前 Job 的 `JENKINS_MODULE_CASE_PATH` | 当前模块 pytest 路径；每日全量 Job 必须为每个模块配置独立默认值 |
| `MODULE_NAME` | 否 | 空 | Jenkins 展示用模块名 |
| `RETRY_COUNT` | 否 | `0` | pytest rerun 次数，默认不重跑 |
| `CLEAN_ALLURE` | 否 | `true` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 否 | `false` | CI 中保持 false |

### 脚本 2：失败重试

- **建议脚本文件**：`jenkins/scripts/failed-rerun-pipeline.groovy`
- **建议 Jenkinsfile**：`jenkins/Jenkinsfile.failed-rerun`
- **触发方式**：人工或后续后端触发，无 cron。
- **关键参数**：

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `CASE_PATH` | 是 | `test_case/test_gbif_case` | 当前模块 pytest 路径，用于上下文和报告命名 |
| `PYTEST_NODE_IDS` | 是 | 空 | 失败用例 node id，支持换行或英文逗号分隔 |
| `RETRY_COUNT` | 否 | `0` | pytest rerun 次数 |
| `CLEAN_ALLURE` | 否 | `true` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 否 | `false` | CI 中保持 false |

### 脚本 3：模块重试

- **建议脚本文件**：`jenkins/scripts/module-rerun-pipeline.groovy`
- **建议 Jenkinsfile**：`jenkins/Jenkinsfile.module-rerun`
- **触发方式**：人工或后续后端触发，无 cron。
- **关键参数**：

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `CASE_PATH` | 是 | `test_case/test_gbif_case` | 当前模块 pytest 路径 |
| `MODULE_NAME` | 否 | 空 | Jenkins 展示用模块名 |
| `RETRY_COUNT` | 否 | `0` | pytest rerun 次数 |
| `CLEAN_ALLURE` | 否 | `true` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 否 | `false` | CI 中保持 false |

### 共享脚本要求

- 共享逻辑可保留或重构到 `jenkins/scripts/api-test-pipeline.groovy`。
- Jenkins Groovy 只做参数、stage、跨平台命令和产物归档，不复制 pytest 选择、失败重试或 Allure summary 解析核心逻辑。
- 所有脚本必须兼容 Windows `bat` 和 Linux `sh`。
- 脚本必须支持本地挂载仓库时跳过 `checkout scm`，继续兼容 `LOCAL_WORKSPACE_REPO=true`。

---

## §8 Jenkins Job 参数界面与人工验收说明 [必填]

> 本阶段不新增平台 Vue 页面；UI 阶段产物改为 Jenkins 参数界面和人工验收交互说明，供主人在 Jenkins 上配置和验收。

| Jenkins Job | 页面目标 | 参数展示 | 操作反馈 | 验收重点 |
| --- | --- | --- | --- | --- |
| 每日全量模块执行 Job | 每个模块一个 Job，凌晨 2 点自动执行 | `CASE_PATH`、`MODULE_NAME`、`RETRY_COUNT`、`CLEAN_ALLURE`、`OPEN_REPORT` | Jenkins build、console log、artifact、Allure 发布 | cron 存在；模块路径正确；产物完整 |
| 失败重试 Job | 执行传入失败 node id | `CASE_PATH`、`PYTEST_NODE_IDS`、`RETRY_COUNT`、`CLEAN_ALLURE`、`OPEN_REPORT` | node id 为空时明确失败；有 node id 时只执行目标用例 | 与勾选失败重试/一键失败重试共用 |
| 模块重试 Job | 执行当前模块全部用例 | `CASE_PATH`、`MODULE_NAME`、`RETRY_COUNT`、`CLEAN_ALLURE`、`OPEN_REPORT` | Jenkins build、artifact、Allure 发布 | 后续同步会更新日期/执行时间 |

---

## §9 架构影响评估 [必填 · 质量门禁]

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | Jenkins 负责执行主干；`api-test` 负责 pytest、失败 node id 和 Allure 产物；DRF/Vue 执行对接后置。 |
| 数据模型 | 否 | 本阶段不新增数据库表；后续仍新增 `jenkins_task` 和 `module_execution_lock`。 |
| 权限 | 是 | 本阶段由 Jenkins 自身权限控制 Job 执行；平台 Cookie 只保护平台 API，不保护 Jenkins/Allure 外链。 |
| Jenkins 执行链路 | 是 | 新增/重构 3 条 Pipeline 脚本，是本阶段核心交付。 |
| `api-test` 执行协议 | 是 | 脚本必须与 `ci_runner --from-jenkins-env` 参数保持一致；如需扩展 runner，必须 TDD。 |
| 报告 / Allure 协议 | 是 | 继续归档 runtime 产物并尝试发布 Allure；不提交报告产物。 |
| Docker Compose 部署 | 是 | 推荐使用 `docker-compose.jenkins-tools.yml` 工具链镜像或在 Jenkins agent 预装 Python/Allure；不得写死本机路径。 |
| 安全 | 是 | 不提交 Jenkins 凭据、真实生产 URL、Cookie、token、运行产物或 Allure HTML。 |

## §10 容器化兼容检查 [必填 · 质量门禁]

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 有风险 | Jenkins Job 使用 workspace 相对路径和 `JENKINS_API_TEST_DIR`，每日全量模块路径使用 per-job 环境变量 `JENKINS_MODULE_CASE_PATH`，不写死个人目录。 |
| 宿主机固定端口 | 否 | 本阶段脚本不依赖固定宿主端口；Jenkins 访问地址仍由 `.env` 注入。 |
| 真实凭据 | 有风险 | Jenkins 凭据只放 Jenkins Credentials 或私有环境变量，不写入 Groovy、README、`.env.example`。 |
| 不可迁移业务常量 | 有风险 | 默认 `CASE_PATH` 可使用示例模块；真实模块由 Jenkins Job 参数配置。 |
| 手工 Jenkins 配置依赖 | 是 | 本阶段验收需要主人在 Jenkins 上创建 3 类 Job；README 必须写清配置步骤。后续可单独建设 Job DSL/JCasC。 |

## §11 非功能要求 [S可简]

- **可靠性**：脚本参数缺失时必须明确失败，不允许静默跑错范围。
- **可观测性**：每次执行必须输出 summary、failed node ids、console log、Allure results/report，并由 Jenkins 归档。
- **兼容性**：Windows/Linux agent 均可执行；本地挂载仓库和真实 scm checkout 均可执行。
- **安全**：不提交真实凭据和运行产物；Jenkins/Allure 外链不额外套平台 Cookie 验证。
- **可维护性**：三条业务脚本可读清晰，共享重复逻辑，避免三个脚本复制大段命令。

---

## §12 验收口径汇总 [必填]

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC-JENKINS-1.1 | 每个模块每日全量 Job 支持凌晨 2 点自动执行 | F2 |
| AC-JENKINS-1.2 | 每日全量手工触发后产物完整 | F2 |
| AC-JENKINS-1.3 | 每日全量归档 runtime 并可查看 Allure | F2 |
| AC-JENKINS-1.4 | 每日全量后续同步会更新日期和执行时间 | F2 |
| AC-JENKINS-2.1 | 失败重试只执行传入 node id | F6 |
| AC-JENKINS-2.2 | 失败重试未传 node id 明确失败 | F6 |
| AC-JENKINS-2.3 | 失败重试产物完整 | F6 |
| AC-JENKINS-2.4 | 失败重试后续同步不更新日期和执行时间 | F6 |
| AC-JENKINS-3.1 | 模块重试执行当前模块全部用例 | F7 |
| AC-JENKINS-3.2 | 模块重试产物完整 | F7 |
| AC-JENKINS-3.3 | 模块重试后续同步会更新日期和执行时间 | F7 |

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-04 | v0.1 | 起草“Jenkins 任务与报告入口”需求说明，列出 Q1-Q8 | 进入 P4 需求 loop |
| 2026-07-04 | v0.2 | 合并 Jenkins/Docker/env 调研，新增 Q9/Q10 | 区分内部 Jenkins API 与公开跳转 |
| 2026-07-05 | v0.3 | 按主人裁决重定向 P4：本阶段先交付 Jenkins 三条流水线脚本，前后端执行对接后置 | 主人明确本阶段要先在 Jenkins 上配置验收三类流水线 |
| 2026-07-05 | v1.0 | Q11 按“全部采纳推荐”闭环，需求说明冻结 | 满足需求澄清冻结门禁，进入测试用例和 Jenkins TDD |
| 2026-07-05 | v1.1 | 补充每日全量 per-job `JENKINS_MODULE_CASE_PATH` 默认值和缺失失败要求 | 独立审查发现 cron 可能跑示例默认模块，已回写契约 |

---

## §14 冻结确认（主人签字门禁）

- [x] §0 待澄清清单全部闭环（无“待确认”状态）
- [x] §9 架构影响评估已完成
- [x] §7 Jenkins 脚本契约完整、可冻结
- [x] §10 容器化兼容检查通过
- [x] §4 每个功能点都有可测的 Given-When-Then 验收标准

**冻结人（主人）**：`主人`　　**冻结日期**：`2026-07-05`

> 冻结后，下游「功能测试用例 → Jenkins Job 参数说明/UI 交互说明 → Jenkins 脚本 TDD → 独立审查 → RTM → 验收包」自动衔接推进。
> 撞到本文未覆盖的关键决策，必须暂停上报主人并回写 §0 与 §13，严禁脑补。
