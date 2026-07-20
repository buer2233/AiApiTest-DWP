# Stage13-Daily-Full-Module-单一流水线编排需求说明

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | Stage13-Daily-Full-Module-单一流水线编排 |
| 需求分级 | L |
| 裁剪说明 | 不裁剪。本需求影响 Jenkins Job 创建策略、执行并发协议、Allure 聚合、后端同步与前端任务展示。 |
| 关联模块 | api-test / back-end / front-end / jenkins / docker |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |

## §0 待澄清清单（澄清门禁）

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | 每类 Pipeline 的“最多 10 个 Job 并发”具体边界。 | Daily、模块重试、失败重试各自独立限流至最多 10 个 Job；不同类型同时运行时全系统并发可超过 10。Daily 内部的模块并发实现仍需遵循此边界。 | 已确认：按 Pipeline 类型独立限制，不能作为全局总上限。 | 已确认 |
| Q2 | 后端和前端对一次 Daily 执行的任务展示粒度。 | A. 仅展示一条父 Daily 任务，模块结果只更新快照；B. 展示一条父任务及模块子任务；C. 继续展示多个模块任务但共同关联一个父 Job。影响数据模型、同步 API、页面与审计。 | 已确认：仅展示一条父 Daily 任务；模块结果不生成或展示模块子任务，只更新模块快照。 | 已确认 |
| Q3 | Allure 报告与失败处理策略。 | A. 仅生成并入口到父级聚合 Allure；B. 聚合报告加模块报告入口；失败重试继续沿用现有独立失败/模块重试 Job 或纳入 Daily 后续步骤。影响归档结构、报告 API 与存储。 | 已确认：Daily 仅提供父级聚合 Allure；模块明细只保留在该构建归档与汇总产物中。模块重试和失败重试继续使用各自独立 Pipeline 的报告与失败处理语义。 | 已确认 |
| Q4 | 旧分模块 Daily Job 和历史绑定的迁移策略。 | A. 新 Pipeline 验收后禁用定时器并保留历史；B. 验收后删除；C. 保留一段并行观察期。影响切换风险、历史同步和运维操作。 | 已确认：新 Daily Pipeline 通过最终验收后删除旧分模块 Daily Job；删除同时移除其 Jenkins 构建历史。 | 已确认 |
| Q5 | 定时策略与手动触发参数。 | 是否继续每日 `02:00`，以及手动触发是否允许选择环境/模块子集、并发上限（最大 10）和是否清理历史 Allure。影响参数契约和验收范围。 | 已确认：固定每日 `02:00`；定时和手动触发均执行全部活跃模块；并发上限固定为 10。 | 已确认 |
| Q6 | Daily 的“全部活跃模块”清单权威来源。 | A. `api-test/utils/package_module.yaml`；B. 后端 `TestModule.is_active`；C. 两者交叉校验。影响 Jenkins init/runtime 的配置方式、模块增删流程和漂移处理。 | 已确认：`api-test/utils/package_module.yaml` 是唯一权威来源；Jenkins 只读取仓库配置，后端消费汇总结果更新模块快照。 | 已确认 |
| Q7 | Daily 中部分模块失败时的父构建状态和调度行为。 | A. 继续运行全部模块，全部完成后父构建失败；B. 首个失败立即停止未开始模块；C. 全部完成但父构建标记不稳定/成功。影响报告完整性、告警与模块快照完整度。 | 已确认：继续执行全部模块；全部完成、汇总和归档后，父构建标记为失败。 | 已确认 |
| Q8 | 同一 Pipeline 类型已达到 10 个并发 Job 时的新请求如何处理。 | A. Jenkins 排队等待同类型容量；B. 手动触发立即拒绝，定时触发跳过；C. 仅保留一个待执行请求，其余拒绝。影响 Jenkins 队列、后端 API 错误码和使用体验。 | 已确认：进入 Jenkins 队列，待所属 Pipeline 类型释放容量后自动执行；类型之间互不占用配额。 | 已确认 |
| Q9 | Daily 目标测试环境范围与 URL 覆盖。 | 默认环境与手动传入其他 URL 的关系、模块清单在环境切换时是否变化。 | 已确认：模块始终为 YAML 全量；未传 URL 时使用当前私有配置默认值；Jenkins 支持以 URL 参数覆盖为其他测试环境。 | 已确认 |
| Q10 | 单一 Daily 的多模块编排方式。 | A. 唯一 Daily 父 Job + 无定时 Daily Worker Job，按 Worker Job 分类限流；B. 在父 Job 内以 Pipeline 分支节流；C. 资源锁方式限流。影响 Jenkins 队列语义、跨父构建限流、模块工件回收和父级 Allure 聚合。 | 已确认：采用 A。父 Job 只负责编排、等待、汇总和唯一 Allure；Daily Worker 无定时器，按 Daily 类型分类限流为最多 10 个并发 Job。 | 已确认 |
| Q11 | `TARGET_BASE_URL` 覆盖值与平台已登记测试环境的映射。 | A. 仅允许匹配已启用 `TestEnvironment` 的 URL；B. 允许任意合法 URL，并自动创建环境记录；C. 允许任意合法 URL，但只执行和归档、不更新模块快照。影响父任务环境外键、模块快照归属与审计。 | 已确认：仅允许匹配已启用 `TestEnvironment` 的 URL。未匹配时在调度任何模块前失败，不创建父任务、不更新模块快照。 | 已确认 |
| Q12 | Daily 父 Job 对已登记环境的调度前校验机制。 | A. 调用后端只读预检 API，由 `TestEnvironment` 作为唯一事实源；B. 在 Jenkins / `api-test` 维护第二份版本化环境清单；C. 运行结束后由后端同步时再拒绝。影响凭据、环境单一事实源和失败时机。 | 已确认：在测试框架维护版本化环境清单 `api-test/utils/package_environment.yaml`。Jenkins 仅从该文件校验并解析环境，后端将其同步为 `TestEnvironment` 用于快照、任务与审计。 | 已确认 |
| Q13 | 环境从 `package_environment.yaml` 删除时的后端保留策略。 | A. 同步时标记为停用，保留历史任务、快照和趋势；B. 级联删除所有关联数据；C. 保留为启用状态直到人工处理。影响历史审计、外键约束和 URL 可用范围。 | 已确认：同步时标记为停用，保留历史任务、快照和趋势。 | 已确认 |
| Q14 | 平台 CRUD 修改环境后，Jenkins 写回版本化 YAML 的 Git 持久化策略。 | A. Jenkins 自动提交并推送；B. 只修改当前受控工作区，等待人工提交；C. 不改 YAML，仅在 MySQL 保存。影响凭据、可追溯性、容器化与多副本一致性。 | 已确认：Jenkins 自动提交并推送受控主干。仅允许工作区干净、远端可快进时写入；推送失败保留 MySQL 变更并标记待同步。 | 已确认 |
| Q15 | MySQL CRUD 与手工 YAML 编辑同时发生时的冲突策略。 | A. 使用 YAML SHA 修订号检测冲突，拒绝自动覆盖并要求管理员先导入或重新提交；B. MySQL 写回永远覆盖 YAML；C. YAML 导入永远覆盖 MySQL。影响数据丢失风险和同步操作体验。 | 已确认：使用 YAML SHA 修订号检测冲突，拒绝自动覆盖；管理员须先导入 YAML 或重新提交平台修改。 | 已确认 |

## §1 需求背景与目标

- **背景**：当前系统根据 `package_module.yaml` 为每个模块创建并定时运行一个 Daily Job；Jenkins 显示多个 `${JENKINS_DAILY_FULL_JOB_PREFIX}-<module>` Job。测试环境又仅由后端硬编码种子维护，页面只读，不能安全地把平台环境、测试框架 YAML 和 MySQL 对齐。
- **目标**：收敛为唯一的 `AiApiTest-DWP-Daily-Full-Module` Pipeline；该 Pipeline 固定于每日 `02:00` 调度 YAML 全量模块，最多 10 个 Daily Worker 并发，完成汇总、失败处理和唯一 Allure 归档。新增版本化环境清单及环境通过率页 CRUD，使 MySQL、YAML 和 Daily 目标环境保持可追溯同步。
- **成功指标 / 价值**：仅一个被定时调度的 Daily 入口；每个构建可追溯全量模块、目标环境和聚合结果；管理员可安全维护测试环境，且 YAML 与 MySQL 不会被静默互相覆盖。

## §2 范围

- **做（in scope）**：单一 Daily Job 的创建/修复与固定 `02:00` 定时策略；从 `api-test/utils/package_module.yaml` 发现模块；受限并发编排；模块结果和父级汇总的稳定产物协议；Allure 归档；新增 `api-test/utils/package_environment.yaml`；测试环境通过率页面的环境 CRUD；MySQL 与 YAML 的双向同步、同步状态和审计；后端同步、接口与前端展示的必要调整；切换策略与回归测试。
- **不做（out of scope）**：不改变模块重试、失败重试、pytest 失败 node id 的业务语义；不新增平台侧 Daily 手动触发入口；不允许后端容器直接写宿主机源码；不在最终验收通过前删除旧分模块 Daily Job 或其 Jenkins 历史。最终验收通过后的受控删除是 Q4 已确认迁移步骤。

## §3 用户角色与权限矩阵

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| `admin` | 查看环境快照和 Daily 父任务；环境新增、编辑、停用/恢复；发起 YAML 导入、查看和重试同步请求 | 不可绕过 YAML SHA 冲突检查；不可在平台选择 Daily 模块子集 | 启用与停用环境、同步审计、全部任务与报告入口 |
| `member` | 查看启用环境、环境快照、模块快照、Daily 父任务和父级 Allure | 环境 CRUD、导入、同步重试、停用/恢复 | 仅启用环境及被授权的既有任务/报告 |
| Jenkins 配置同步 Job | 读取隔离 SCM checkout 中的 YAML；回调受限内部 API；自动 Git 提交并推送 | 不访问 MySQL；不使用开发挂载工作区；不执行 pytest | 仅本次同步请求的规范化配置快照 |

本需求不新增平台侧 Daily 手动触发入口；Jenkins 管理员仍可在 Jenkins 页面手动构建。`TARGET_BASE_URL` 仅接受 `api-test/utils/package_environment.yaml` 中声明、并已同步为启用 `TestEnvironment` 的 URL。

## §4 功能清单与验收标准

### F1 单一 Daily 父流水线

- **能力**：唯一 Daily 父 Job 在每日 `02:00` 或 Jenkins 手动构建时，读取 `package_module.yaml` 的全部模块；为每个模块触发无定时 Daily Worker。父 Job 只编排、等待、汇总和发布父级 Allure。
- **关联数据**：`JenkinsJobBinding`、`JenkinsTask`、`TestRun`、`ModuleSnapshot`、`ModuleRunHistory`。
- **验收标准**：
  - `AC1.1` Given 初始化完成 When 查看 Jenkins Job Then 仅 `AiApiTest-DWP-Daily-Full-Module` 具有 `0 2 * * *`，Daily Worker 无定时器且不创建每模块 Daily 定时 Job。
  - `AC1.2` Given 同时存在多个 Daily 父构建 When 各父构建调度 Worker Then Daily Worker 全局最多 10 个执行，超额 Worker 在 Jenkins 队列等待；模块重试和失败重试各自仍可同时最多执行 10 个。
  - `AC1.3` Given 任一 Worker 的测试结果失败 When 其余模块尚未执行 Then 父 Job 继续等待并运行全部模块，全部结果、聚合摘要和 Allure 完成后父构建为失败。
  - `AC1.4` Given `TARGET_BASE_URL` 为空或为已登记 URL When 父 Job 开始 Then 空值解析为当前私有默认 URL，非空值复用 `--base-url` 校验并精确匹配环境 YAML；两者都执行 YAML 全量模块。
  - `AC1.5` Given 模块或环境 YAML 为空、格式不合法、URL 未登记或环境未同步 When 父 Job 预检 Then 在触发任何 Worker 前失败，产生结构化诊断且不创建父任务或更新快照。

### F2 父任务、模块快照与报告聚合

- **能力**：Daily 仅向平台暴露一个父任务和一个父级 Allure；模块明细只存在于父构建归档和聚合摘要，并逐模块更新既有快照、失败用例与趋势。
- **关联数据**：`TestRun`、`JenkinsTask`、`ModuleSnapshot`、`TestCaseResult`、`ModuleRunHistory`。
- **验收标准**：
  - `AC2.1` Given 一次 Daily 构建包含多个模块 When 后端同步完成 Then 仅创建一条 `daily_full` 父 `JenkinsTask` 和一条 module 为空的 `TestRun`，不创建 Daily 模块子任务。
  - `AC2.2` Given 所有 Worker 产物可读取 When 父 Job 汇总 Then 父运行目录含稳定 `summary.json`、全部模块明细和合并后的 Allure 原始结果；前端仅显示父级 Allure 入口。
  - `AC2.3` Given 聚合摘要含模块结果 When 后端同步 Then 每个模块按摘要更新对应环境快照、失败用例和趋势；任一模块解析失败只影响父任务失败诊断，不掩盖其他模块已完成结果。

### F3 测试环境目录双向同步

- **能力**：环境 YAML 是 Jenkins 的调度前清单，MySQL 是平台查询与审计投影。admin 在页面 CRUD 后先写 MySQL，再经 Jenkins 同步 Job 自动写 YAML、提交和推送；手工 YAML 修改后可从页面导入 MySQL。
- **关联数据**：`TestEnvironment`、`EnvironmentCatalogState`、`EnvironmentCatalogSyncAttempt`。
- **验收标准**：
  - `AC3.1` Given `package_environment.yaml` When 解析 Then 顶层 `env_key` 唯一且每项仅含必填 `base_url`、`url_name`、`url_desc`；URL 统一去尾斜杠，重复 key 或 URL、无协议/域名、空名称或未知字段均为非法。
  - `AC3.2` Given admin 新增、编辑、停用或恢复环境 When 请求通过校验 Then MySQL 在单一事务中更新并创建一条 `mysql_to_yaml` 同步请求；环境 key 创建后不可改名，停用为逻辑删除并从 YAML 导出清单移除。系统始终至少保留一个启用环境；DELETE 或 PATCH 试图停用最后一个启用环境时返回 `409 last_active_environment`，不更新 MySQL 且不创建同步请求。
  - `AC3.3` Given `mysql_to_yaml` 请求排队 When Jenkins 配置同步 Job 成功 Then 在隔离 SCM checkout 中校验期望 YAML blob SHA，生成确定性 YAML，自动提交、快进推送受控主干，并将目录状态更新为 `synced`。
  - `AC3.4` Given admin 手工修改 YAML 后点击“同步测试环境数据” When YAML 合法 Then Jenkins 读取隔离 checkout 的 YAML，后端在单一事务中新增、更新存在项并停用缺失项，保留所有历史关联数据。
  - `AC3.5` Given YAML 校验、Git 拉取、提交或推送失败 When 同步结束 Then MySQL 已提交的 CRUD 不回滚，目录和请求状态可见为 `failed` 或 `pending`，可重试且不产生半更新。
  - `AC3.6` Given 当前 YAML blob SHA 不等于请求的期望 SHA When Jenkins 尝试写回 Then 状态为 `conflict`，不改 YAML、不提交 Git；页面要求管理员先导入 YAML 或重新提交平台修改。
  - `AC3.7` Given member 调用环境写接口或访问管理控件 When 请求或页面加载 Then API 返回 `403 admin_required`，页面不展示 CRUD、导入或重试控件。
  - `AC3.8` Given 首次部署或重建后执行环境初始化 When 后端建立环境投影 Then 旧硬编码 `seed_environment` 改为读取随镜像复制的环境 YAML，确保当前默认环境可用；运行时手工 YAML 变更仍只由页面触发 Jenkins 导入。

### F4 受控迁移

- **能力**：旧分模块 Daily Job 仅在全部新契约验收通过后删除。
- **验收标准**：
  - `AC4.1` Given 新 Pipeline 未通过最终验收 When Jenkins 初始化或同步 Then 旧分模块 Daily Job 与构建历史不被删除。
  - `AC4.2` Given 验收包已获主人最终签字 When 执行版本化迁移 Then 删除旧分模块 Daily Job 及其 Jenkins 构建历史，保留唯一 Daily 父 Job 和平台数据库历史。

## §5 状态机定义

### Daily 父任务

| 源状态 | 事件 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| 无 | Jenkins 父 Job 预检失败 | 无 | 模块 YAML、环境 YAML 或目标 URL 无效 | 仅保留 Jenkins 构建结构化诊断；不创建平台父任务、`TestRun` 或快照更新 |
| 无 | Jenkins 父 Job 预检通过 | `queued` | 模块 YAML、环境 YAML、目标 URL 均有效 | 后端发现后创建唯一父任务 |
| `queued` | 开始编排 | `running` | 父任务未取消 | 触发全部 Worker |
| `running` | 所有 Worker、聚合、归档成功 | `success` | 无模块失败 | 同步父摘要和模块快照 |
| `running` | 存在测试失败 | `test_failed` | 全部模块已完成且聚合成功 | Jenkins 父构建为 `FAILURE`，同步全部模块结果 |
| `running` | Worker、聚合或归档基础设施失败 | `failed` | 已尽力等待全部可调度模块 | 保留已成功模块结果和诊断 |
| `queued` / `running` | 取消 | `canceling` -> `canceled` | Jenkins 取消成功 | 不创建模块子任务 |

### 环境配置同步请求

| 源状态 | 事件 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| 无 | CRUD 或导入请求创建 | `pending` | 无其他活动同步请求 | 冻结导出快照或导入意图 |
| `pending` | Jenkins 接受 | `queued` | 仅一个配置同步 Job | 保存 queue id |
| `queued` | Job 开始 | `running` | | 保存 build 信息 |
| `running` | 回调校验和 Git 推送成功 | `synced` | blob SHA 匹配；导入 YAML 合法 | 更新目录 blob SHA、commit SHA 和同步时间 |
| `running` | blob SHA 不一致 | `conflict` | | 不改 YAML、不提交 Git |
| `pending` / `queued` / `running` | Jenkins、YAML 或 Git 失败 | `failed` | | 保留 MySQL 数据、错误码和可重试诊断 |
| `failed` / `conflict` | admin 重试或重新提交 | `pending` | `conflict` 须先完成 YAML 导入或重新编辑 | 创建新的不可变请求 |

同一时刻仅允许一个非终态环境配置同步请求；新的环境写入、导入和重试返回 `409 environment_config_sync_busy`，防止异步写入重排。环境生命周期为 `active -> inactive -> active`，不物理删除，且系统始终至少保留一个启用环境。

## §6 数据表设计

### `test_environment`（扩展）

| 字段 | 类型建议 | 必填 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- |
| `env_key` | varchar(64) | 是 | YAML 顶层键；创建后不可修改 | 唯一 |
| `env_name` | varchar(128) | 是 | 映射 YAML `url_name` | 普通索引 |
| `base_url` | varchar(512) | 是 | 映射 YAML `base_url`，规范化去尾斜杠 | 全局唯一 |
| `url_desc` | text | 是 | 映射 YAML `url_desc` | 无 |
| `is_active` | bool | 是 | 停用即逻辑删除且不导出至 YAML；不可停用最后一个启用环境 | 索引 |

现有运行、快照和审计关联保持不变；停用不得物理删除任何历史记录。

### `environment_catalog_state`（新增单例）

| 字段 | 类型建议 | 必填 | 说明 | 约束 |
| --- | --- | --- | --- | --- |
| `catalog_key` | varchar(64) | 是 | 固定 `package_environment` | 唯一 |
| `yaml_blob_sha` | char(40) | 否 | 最近成功同步的 Git YAML blob SHA，不使用仓库 HEAD SHA | 索引 |
| `status` | varchar(32) | 是 | `synced/pending/queued/running/conflict/failed` | 索引 |
| `last_commit_sha` | char(40) | 否 | 最近成功写回提交 | 无 |
| `last_synced_at` | datetime | 否 | 最近成功同步时间 | 索引 |
| `last_error_code` / `last_error_summary` | varchar/text | 否 | 脱敏诊断 | 无 |

### `environment_catalog_sync_attempt`（新增追加审计）

| 字段 | 类型建议 | 必填 | 说明 | 约束 |
| --- | --- | --- | --- | --- |
| `direction` | varchar(32) | 是 | `mysql_to_yaml` 或 `yaml_to_mysql` | 索引 |
| `status` | varchar(32) | 是 | 同 §5 状态机 | 索引 |
| `expected_yaml_blob_sha` / `observed_yaml_blob_sha` | char(40) | 否 | 冲突检测依据 | 无 |
| `payload_json` / `payload_sha256` | json / char(64) | 否 | 冻结的非敏感配置快照及摘要 | 无 |
| `queue_id` / `build_number` / `jenkins_build_url` | varchar/int/varchar | 否 | Jenkins 可追溯信息 | 唯一约束 job + build |
| `job_full_name` | varchar(255) | 是 | 专用环境配置同步 Job 名 | 与 build 组成唯一键 |
| `commit_sha` | char(40) | 否 | 成功推送后的提交 | 无 |
| `requested_by` | FK UserAccount | 否 | 发起 admin；系统触发为空 | 索引 |
| `error_code` / `error_summary` | varchar/text | 否 | 脱敏失败原因 | 无 |
| `created_at` / `finished_at` | datetime | 是 / 否 | 审计时间 | 索引 |

Daily 建模调整：`JenkinsJobBinding` 的 `daily_full` 绑定允许 `environment`、`module` 都为空，表示全局父 Job；重试绑定仍同时要求环境和模块。`JenkinsTask.module` 允许为空以表示 Daily 父任务，`JenkinsTask.environment` 和 `TestRun.environment` 始终非空；模块结果通过父摘要更新既有快照。

## §7 API 契约

所有浏览器接口使用现有 Cookie JWT；写接口均要求 admin。成功体沿用 `{ "data": ... }`，错误体沿用现有 `api_error_response`。

| 方法与路径 | 权限 | 请求与校验 | 成功响应 | 错误语义 |
| --- | --- | --- | --- | --- |
| `GET /api/v1/test-environments` | 登录用户 | `is_active=true|false` 可选 | 环境列表和当前目录状态 | `401` |
| `POST /api/v1/test-environments` | admin | `env_key`、`url_name`、`base_url`、`url_desc`；key 与 URL 全局唯一 | `202`：环境与 `sync_attempt` | `400 validation_error`、`409 environment_config_sync_busy/duplicate_environment`、`403 admin_required` |
| `PATCH /api/v1/test-environments/{id}` | admin | 仅 `url_name/base_url/url_desc/is_active`；不可改 key；不可停用最后一个启用环境 | `202`：环境与 `sync_attempt` | `404`、`409 environment_config_sync_busy/last_active_environment`、`403` |
| `DELETE /api/v1/test-environments/{id}` | admin | 无请求体；逻辑停用；不可停用最后一个启用环境 | `202`：停用环境与 `sync_attempt` | `404`、`409 environment_config_sync_busy/last_active_environment`、`403` |
| `POST /api/v1/test-environments/sync-from-yaml` | admin | 无请求体 | `202`：`yaml_to_mysql` 请求 | `409 environment_config_sync_busy`、`403` |
| `GET /api/v1/environment-catalog-sync-attempts/{id}` | admin | 无 | 单次同步状态、错误、Jenkins 与提交信息 | `404`、`403` |
| `POST /api/v1/environment-catalog-sync-attempts/{id}/retry` | admin | 无；冲突态先导入 YAML 或重新创建写请求 | `202`：新请求 | `409 sync_not_retryable/environment_config_sync_busy`、`403` |

内部 Jenkins 契约不向浏览器开放：专用同步 Job 仅以私有服务令牌调用 `GET {JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL}/api/v1/internal/environment-catalog-sync-attempts/{sync_request_id}/export/` 和 `POST {JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL}/api/v1/internal/environment-catalog-sync-attempts/{sync_request_id}/callback/`。服务基址只从私有环境变量读取，不能作为 Jenkins 构建参数、浏览器响应或日志字段；`sync_request_id` 必须是安全不透明标识，专用 Job 在调用命令前校验其格式和 40 位小写 blob SHA。后端从不读取容器外文件；Daily 父 Job 从 YAML 校验环境但不访问 MySQL。既有 `GET /test-environments/{id}/summary`、任务列表与父级 Allure URL 保持兼容，Daily 不增加模块子任务 API。

## §8 UI 字段级规格

路由保持 `/environments`，不新增子任务页面。UI 原型阶段必须将本映射作为范围冻结依据。

| 区域 | 处理方式 | 路由 / 组件 | 字段与交互 |
| --- | --- | --- | --- |
| R1 环境快照主体 | 当前页面直接展示 | `/environments` `EnvironmentsView` | 保留环境选择、通过率、统计和模块页链接；只选择启用环境 |
| R2 环境管理表 | 当前页面直接展示，仅 admin | `EnvironmentsView` 管理区 | 展示 key、名称、URL、描述、启停、目录同步状态、最近错误和操作；member 不渲染 |
| R3 新增 / 编辑环境 | 弹窗 | `EnvironmentEditorDialog` | 表单校验、提交后显示 `pending/queued/running` 同步状态；编辑时 key 只读 |
| R4 YAML 导入、冲突和重试 | 弹窗 / 抽屉 | `EnvironmentCatalogSyncDialog` | 发起导入、轮询请求、查看 Jenkins 链接和脱敏错误；冲突仅显示“先导入 YAML”或“重新提交” |

设计标注层、模块子任务、模块级 Allure 入口及不存在的 Daily 平台触发按钮均不得进入 DOM、截图验收或 Playwright 断言。

## §9 架构影响评估

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | `api-test` 管理模块/环境 YAML、单模块执行和聚合工具；Jenkins 编排 Worker 与配置同步；后端管理投影、审计和 API；前端只通过 DRF 展示。 |
| 数据模型 | 是 | Daily 父任务 module 可空；增加环境目录状态与追加同步审计；环境删除改为停用。 |
| 权限 | 是 | admin 才能管理环境与同步；Jenkins 使用最小权限服务令牌和 Git Credentials；member 保持只读。 |
| Jenkins 执行链路 | 是 | 新增唯一 Daily 父 Job、无定时 Worker、三类独立 10 并发分类、专用串行环境配置同步 Job。 |
| `api-test` 执行协议 | 是 | 新增环境 YAML 校验/解析和 Daily 聚合协议；pytest/重试仍仅在 `ci_runner.py`。 |
| 报告 / Allure 协议 | 是 | Daily 只发布父级聚合 Allure；模块明细仅归档；重试 Pipeline 维持独立报告语义。 |
| Docker Compose 部署 | 是 | backend 镜像复制环境 YAML 供固定构建使用；运行时 YAML 导入/导出一律走 Jenkins 隔离 SCM checkout，使用服务名和私有变量。 |
| 安全 | 是 | YAML 禁止 URL 凭据和真实生产地址；Git/服务令牌只在 Jenkins Credentials 或本地 `.env`；错误信息脱敏。 |

## §10 容器化兼容检查

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 否（目标） | 新增脚本仅使用 Jenkins workspace 相对路径和 Compose 服务名。 |
| 宿主机固定端口 | 否（目标） | Job/API 配置使用环境变量，不在脚本中写死公开端口。 |
| 真实凭据 | 否（目标） | 凭据仅由 Jenkins Credentials 或私有环境变量注入。 |
| 不可迁移业务常量 | 否（目标） | 模块和环境均由 YAML 发现；不固化模块名、环境 URL 或宿主机路径。 |
| 手工 Jenkins 配置依赖 | 否（目标） | 父 Job、Worker、限流分类和环境同步 Job 均由版本化 init Groovy 幂等创建/修复。 |
| 容器运行时直接改源码 | 不允许 | backend 不挂载仓库；环境 YAML 写回只能在 Jenkins 的隔离、干净 SCM checkout 中完成，绝不写 `LOCAL_WORKSPACE_REPO` 开发挂载目录。 |
| Git 推送凭据 | 私有配置 | Git Credentials ID、服务令牌、作者身份通过 Jenkins Credentials 或根 `.env` 私有变量注入；`.env.example` 仅保留变量说明/占位符。 |

## §11 非功能要求

- Daily、模块重试、失败重试三个 Pipeline 类型必须各自可验证地限制为最多 10 个 Job 并发；不同类型之间不共享全局 10 并发配额。
- Daily 的定时与手动触发均须固定执行全部活跃模块；不提供模块子集选择参数。
- Jenkins controller、runner/agent 的执行器容量与资源配置必须能承载多个类型同时执行；任务超出所属类型配额时须排队，不得跨类型错误阻塞。
- 同一构建的模块结果必须可定位、可聚合，单个模块失败不能掩盖其他模块结果。
- 模块清单为空、配置不合法、Worker/执行器异常、聚合失败和归档失败须有明确可观察诊断。
- 模块清单只从 `api-test/utils/package_module.yaml` 获取；该文件为空或不合法时，Daily 构建须明确失败且不得产生部分调度。
- Daily 任一模块失败时，其他已排队或未开始模块仍须继续执行；待全部模块结果、汇总和聚合 Allure 均产出后，父构建必须标记为失败。
- 同一 Pipeline 类型达到 10 个并发 Job 时，新请求必须在 Jenkins 队列等待该类型容量，不能因其他类型正在执行而被错误阻塞或拒绝。
- 新增环境清单 `api-test/utils/package_environment.yaml`，以稳定 `env_key` 为顶层键，每项必须包含 `base_url`、`url_name`、`url_desc`；格式或必填字段错误时 Daily 在调度前失败。
- 环境通过率页面提供受权限控制的测试环境新增、编辑、停用/删除和“同步测试环境数据”操作。平台 CRUD 先记录 MySQL，再触发 Jenkins 专用配置同步 Job 写回 YAML，自动提交并推送受控主干；手工编辑 YAML 后，admin 点击同步按钮将 YAML 校验并导入 MySQL。写回/导入失败必须可观察、可重试且不产生半更新；YAML SHA 不一致时拒绝自动覆盖，管理员须先导入 YAML 或重新提交平台修改。
- Daily 参数 `TARGET_BASE_URL` 未传时使用当前私有配置默认 URL；传入时必须复用现有 `--base-url` 校验，并精确匹配环境清单及已同步的启用 `TestEnvironment.base_url`。非法、未登记或不同步 URL 在调度任何模块前失败，不创建父任务、不更新模块快照；模块清单不因 URL 覆盖而变化。
- 环境同步 Job 不属于 Daily、模块重试或失败重试配额；它全局串行，且仅在隔离 SCM checkout 干净、目标主干可快进时自动提交/推送。
- YAML 采用 UTF-8、确定性 key 排序、两空格缩进和末尾换行；同步 SHA 使用该文件 Git blob SHA，不能以仓库 HEAD 替代。
- 现有 `seed_environment` 不得继续硬编码环境，首次初始化改为读取随镜像复制的环境 YAML；运行时文件变更仍须走 Jenkins 同步 Job，不能由后端容器直接读写仓库。
- 所有新增环境变量同步更新根 `.env.example`、模块文档和静态测试；真实 Git 凭据、服务令牌、内部地址不提交 Git。

## §12 验收口径汇总

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC1.1 | 唯一 Daily 定时父 Job 与无定时 Worker | F1 |
| AC1.2 | 三类 Pipeline 独立 10 Job 并发与排队 | F1 |
| AC1.3 | 模块失败不中断、父构建最终失败 | F1 |
| AC1.4 | 默认/覆盖 URL 均执行全量模块 | F1 |
| AC1.5 | YAML/URL 预检失败不调度 | F1 |
| AC2.1 | 平台仅存一条 Daily 父任务 | F2 |
| AC2.2 | 父级聚合摘要与唯一 Allure | F2 |
| AC2.3 | 模块快照、失败与趋势逐模块同步 | F2 |
| AC3.1 | 环境 YAML schema 与 URL 唯一校验 | F3 |
| AC3.2 | admin CRUD 先落 MySQL、再建同步请求 | F3 |
| AC3.3 | 隔离 checkout 自动提交并推送 YAML | F3 |
| AC3.4 | 页面导入 YAML 后 MySQL 新增/更新/停用 | F3 |
| AC3.5 | 同步失败可观察、可重试且不半更新 | F3 |
| AC3.6 | blob SHA 冲突拒绝覆盖 | F3 |
| AC3.7 | member 无环境管理权限 | F3 |
| AC3.8 | 环境初始化不再硬编码默认环境 | F3 |
| AC4.1 | 验收前不删除旧 Daily Job | F4 |
| AC4.2 | 验收后受控删除旧 Job 与构建历史 | F4 |

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-19 | 0.1 | 创建澄清中需求规格并记录五项关键决策。 | 根因调查完成，尚未冻结。 |
| 2026-07-19 | 0.2 | Q1 已确认：10 并发按 Pipeline 类型独立限制，非全系统总上限。 | 主人裁决。 |
| 2026-07-19 | 0.3 | Q2 已确认：Daily 仅展示唯一父任务，模块结果仅更新模块快照。 | 主人裁决。 |
| 2026-07-19 | 0.4 | Q3 已确认：Daily 仅提供父级聚合 Allure，模块明细只归档。 | 主人裁决。 |
| 2026-07-19 | 0.5 | Q4 已确认：新 Pipeline 最终验收后删除旧分模块 Daily Job 及其 Jenkins 构建历史。 | 主人裁决。 |
| 2026-07-19 | 0.6 | Q5 已确认：固定每日 `02:00`，定时和手动触发均执行全部活跃模块，并发上限固定为 10。 | 主人裁决。 |
| 2026-07-19 | 0.7 | Q6 已确认：模块清单唯一来源为 `api-test/utils/package_module.yaml`。 | 主人裁决。 |
| 2026-07-19 | 0.8 | Q7 已确认：模块失败不阻断其他模块；全部汇总和归档后父构建标记为失败。 | 主人裁决。 |
| 2026-07-19 | 0.9 | Q8 已确认：同类型超出 10 并发时进入 Jenkins 队列，类型间配额独立。 | 主人裁决。 |
| 2026-07-19 | 1.0 | Q9 已确认：YAML 全量模块；默认私有环境 URL，Jenkins 可传 URL 覆盖。 | 主人裁决。 |
| 2026-07-19 | 1.1 | Q10 已确认：唯一 Daily 父 Job 调度无定时 Daily Worker Job；Worker 受 Daily 分类 10 并发限流，父 Job 汇总并发布唯一 Allure。 | 主人裁决。 |
| 2026-07-19 | 1.2 | Q11 已确认：`TARGET_BASE_URL` 仅允许匹配已启用的 `TestEnvironment`；未匹配时调度前失败且不更新快照。 | 主人裁决。 |
| 2026-07-19 | 1.3 | Q12 已确认：新增测试框架版本化环境清单，Jenkins 从 YAML 预检，后端同步为 `TestEnvironment`。 | 主人裁决。 |
| 2026-07-19 | 1.4 | Q13 已确认：YAML 删除项同步为停用，历史数据保留；新增环境页面 CRUD 与 MySQL/YAML 双向同步范围。 | 主人裁决。 |
| 2026-07-19 | 1.5 | Q14 已确认：平台写回 YAML 由 Jenkins 自动 Git 提交并推送受控主干；失败保留待同步状态。 | 主人裁决。 |
| 2026-07-19 | 1.6 | Q15 已确认：以 YAML SHA 检测并发冲突，拒绝自动覆盖。 | 主人裁决。 |
| 2026-07-19 | 1.7 | 完成可冻结规格：AC、状态机、数据模型、API、UI 映射和容器化检查；纳入 YAML 初始化替代硬编码种子。 | 澄清闭环与独立调查结论。 |
| 2026-07-19 | 1.8 | 主人确认冻结，允许自动衔接测试用例、UI、后端与前端 TDD 阶段。 | 主人签字门禁。 |
| 2026-07-19 | 1.9 | 校准 Daily 预检状态机：预检失败只保留 Jenkins 诊断，不创建平台父任务、`TestRun` 或快照。 | 消除状态机与 AC1.5 的内部矛盾，不改变已冻结的验收决策。 |
| 2026-07-19 | 2.0 | 主人裁决：始终至少保留一个启用测试环境；拒绝停用最后一项，统一返回 `409 last_active_environment`。 | 消除环境逻辑停用与环境 YAML 非空契约的冲突。 |
| 2026-07-20 | 2.1 | 主人裁决：Jenkins 环境目录同步 Job 在成功 push 后回传实际 Git `HEAD` commit SHA，供后端 `mysql_to_yaml` 审计持久化。 | 禁止后端伪造或放宽成功回调的 commit SHA；修复仅在推送成功后执行。 |

## §14 冻结确认（主人签字门禁）

- [x] §0 待澄清清单全部闭环
- [x] §9 架构影响评估已完成
- [x] §7 API 契约完整、可冻结
- [x] §10 容器化兼容检查通过
- [x] §4 每个功能点都有可测的 Given-When-Then 验收标准

**冻结人（主人）**：`主人`　　**冻结日期**：`2026-07-19`
