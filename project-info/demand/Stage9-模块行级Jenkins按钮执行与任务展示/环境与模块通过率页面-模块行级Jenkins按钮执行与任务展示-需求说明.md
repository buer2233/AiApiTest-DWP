# 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 需求说明书

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 |
| 阶段目录 | `Stage9-模块行级Jenkins按钮执行与任务展示` |
| 需求分级 | M |
| 裁剪说明 | 不裁剪。虽然不新增数据表，但本需求影响 DRF Jenkins 同步、Vue 模块行按钮、Jenkins 任务弹窗和真实验收链路，属于跨模块行为补齐。 |
| 关联历史阶段 | P5 Jenkins 执行闭环与平台接入、Stage8 模块通过率筛选与 Jenkins 趋势接入 |
| 文档状态 | 冻结 |

## §0 待澄清清单

| 编号 | 待澄清点 | 历史裁决 / 本次结论 | 状态 |
| --- | --- | --- | --- |
| Q1 | 三个按钮分别触发什么能力 | 一键失败重试调用 `failed_rerun`，模块重试调用 `module_rerun`，Jenkins 任务打开当前模块任务弹窗；沿用 P5/Stage8 冻结契约。 | 已确认 |
| Q2 | Jenkins job 完成后如何更新当前页面 | 沿用 P5/Stage8：DRF 同步 Jenkins build/artifact 后更新任务状态、模块快照、失败用例和趋势；前端轮询任务弹窗时触发同步并刷新模块列表。 | 已确认 |
| Q3 | 失败重试与模块重试交互 | 失败重试直接触发并提示“开始执行失败重试”；模块重试必须展示固定确认文案。 | 已确认 |
| Q4 | 截图红框是否进入前端 | 红框是设计标注层，不进入 DOM 和验收截图。 | 已确认 |

## §1 背景与目标

- 当前 `/modules` 页面已经展示三个按钮，但真实验收中可能出现按钮不可用、点击后只创建 queued 任务、Jenkins job 完成后页面数据不刷新的问题。
- 本阶段目标是把截图中三个按钮配置到已冻结的 Jenkins 执行闭环：点击按钮经 DRF 触发对应 Jenkins job，任务完成后通过同步刷新当前页面展示；Jenkins 任务弹窗按历史详细需求展示任务类型、状态、日期筛选、外链、取消和轮询。

## §2 范围

- **做**：
  - 修复或补齐后端 Jenkins 同步入口，使运行中任务可从 Jenkins 读取最新 build/artifact 并更新平台数据。
  - 修复或补齐前端 Jenkins 任务弹窗轮询策略：弹窗打开时对 `queued/running/canceling` 任务触发 DRF 同步，状态变化后刷新模块列表。
  - 确保一键失败重试、模块重试、Jenkins 任务按钮不因“已有执行中任务”被前端提前禁用，冲突由后端兜底提示。
  - 保证 Job binding 初始化仍通过 `sync_jenkins_job_bindings`，不在前端写死 Jenkins job 名。
  - 补齐后端 pytest、前端 Vitest/Playwright 和验收证据。
- **不做**：
  - 不新增全局 Jenkins 任务页面。
  - 不新增数据表或 migration，除非开发中发现无法满足冻结契约并触发熔断。
  - 不让前端直连 Jenkins。
  - 不提交真实 Jenkins 用户名、API Token、Cookie、运行产物或本机绝对路径。

## §3 功能清单与验收标准

### F1 一键失败重试按钮配置

- 管理人员点击模块行“一键失败重试”后，前端直接调用 `POST /api/v1/module-snapshots/{snapshot_id}/failed-case-retries`，请求体为 `retry_scope=all_failed`。
- 后端使用当前模块全部当前失败用例 node id 触发 Jenkins failed rerun job。
- 成功后前端提示“开始执行失败重试”，并刷新模块列表和任务弹窗数据。
- 验收标准：
  - `AC-S9-1.1` Job binding 存在且有失败用例时，点击后返回 202 并创建 `failed_rerun` Jenkins task。
  - `AC-S9-1.2` Jenkins job 完成并同步后，失败数和通过率刷新，日期与执行时间保持不变。

### F2 模块重试按钮配置

- 管理人员点击“模块重试”后必须出现确认框，确认文案为“模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？”。
- 确认后调用 `POST /api/v1/module-snapshots/{snapshot_id}/module-reruns`，后端触发 Jenkins module rerun job。
- 验收标准：
  - `AC-S9-2.1` 确认后返回 202 并创建 `module_rerun` Jenkins task。
  - `AC-S9-2.2` Jenkins job 完成并同步后，模块统计、日期、执行时间、当前用例结果和趋势刷新。

### F3 Jenkins 任务按钮与任务展示

- 点击“Jenkins 任务”打开当前模块任务弹窗。
- 弹窗支持日期、状态、任务类型筛选，展示任务编号、任务类型、任务名、环境 URL、状态、触发人、开始/结束时间、取消、查看报告、查看 Jenkins 任务。
- 弹窗打开且存在 `queued/running/canceling` 时，每 5 秒触发 DRF 同步并刷新；关闭后停止。
- 验收标准：
  - `AC-S9-3.1` 当前模块有任务时，弹窗按历史字段展示任务。
  - `AC-S9-3.2` 轮询同步到终态后，弹窗状态更新并触发模块列表刷新。
  - `AC-S9-3.3` 查看报告和查看 Jenkins 任务使用后端返回链接新页打开，不嵌入 iframe。

### F4 后端同步健壮性

- Daily 批量同步必须按 active daily job binding 发现 Jenkins build，不因函数签名不匹配而失败。
- 单任务同步 Jenkins 不可用时返回可读错误，不破坏只读页面。
- 验收标准：
  - `AC-S9-4.1` `POST /api/v1/jenkins-tasks/sync` 在 `discover_daily=true` 时会向 Jenkins service 传入 active daily job names。
  - `AC-S9-4.2` `POST /api/v1/jenkins-tasks/{task_id}/sync` 同步完成后返回最新 task。

## §4 数据表设计

不新增表，复用：

- `jenkins_job_binding`
- `jenkins_task`
- `module_execution_lock`
- `module_snapshot`
- `test_case_result`
- `module_run_history`

## §5 API 契约

- 沿用 P5/Stage8 已冻结接口：
  - `POST /api/v1/module-snapshots/{snapshot_id}/failed-case-retries`
  - `POST /api/v1/module-snapshots/{snapshot_id}/module-reruns`
  - `GET /api/v1/module-snapshots/{snapshot_id}/jenkins-tasks`
  - `POST /api/v1/jenkins-tasks/{task_id}/sync`
  - `POST /api/v1/jenkins-tasks/sync`
- 本阶段允许前端新增对 `POST /api/v1/jenkins-tasks/{task_id}/sync` 的调用封装；不新增 URL。

## §6 架构影响评估

| 维度 | 是否影响 | 说明 |
| --- | --- | --- |
| DRF | 是 | 补齐 Jenkins 同步调用和 Daily discovery 参数传递。 |
| Vue | 是 | 补齐任务弹窗轮询同步和刷新模块列表。 |
| Jenkins | 否 | 不改 Jenkinsfile，沿用 P4 三类 job。 |
| api-test | 否 | 不改 runner 协议。 |
| Docker | 否/轻微 | 继续通过 `.env`、Compose 服务名和 Jenkins API 配置。 |
| 数据模型 | 否 | 不新增表。 |
| 权限 | 否 | 沿用 admin 触发、登录用户查看任务、admin/触发人取消。 |
| 报告协议 | 否 | 沿用 Jenkins artifact / Allure 链接。 |

## §7 容器化兼容检查

- 不新增本机绝对路径。
- 不新增固定宿主端口。
- 不提交真实凭据。
- Jenkins API 地址、公开跳转地址和 Job 名继续通过 `.env` / job binding 注入。
- 前端只使用相对 DRF API，不直连 Jenkins。

## §8 冻结确认

- [x] 需求澄清闭环，全部沿用历史冻结裁决。
- [x] API 契约冻结，不新增 URL。
- [x] 架构影响评估完成。
- [x] 容器化兼容检查通过。

**冻结人**：主人历史裁决 + 本次需求指令　　**冻结日期**：2026-07-09
