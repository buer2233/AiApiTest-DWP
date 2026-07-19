# Stage13-Daily-Full-Module-单一流水线编排：调查发现

## 2026-07-20 Task 4 最终审查整改

- 最终审查范围冻结为四项后端韧性缺口：回调语义校验失败必须终结 attempt、Jenkins 调度异常或无 queue id 必须释放同步键、Daily 既有任务两条查询路径均须验证父任务形态、首次 global Daily binding 创建须有 MySQL 跨事务互斥。
- 不新增 migration；global binding 采用 MySQL advisory lock，并保留 SQLite pytest 兼容分支。
- 新增的回调语义错误回归已直接通过，证实服务层已有失败落库和重试键释放逻辑，不修改该项生产代码。

## 已确认事实

- Issue 状态为待处理，并明确要求进入完整需求 loop。
- 当前 Jenkins 存在两个分模块 Daily Job：`AiApiTest-DWP-Daily-Full-Module-test_gbif_case` 与 `AiApiTest-DWP-Daily-Full-Module-test_gbif_case_module2`。
- 目标为唯一 `AiApiTest-DWP-Daily-Full-Module` Pipeline：每日执行当前全量模块，最多 10 个 Job 并发，模块拆分、调度、聚合、失败及 Allure 归档均属于同一 Pipeline 契约。
- Issue 明确禁止本次登记阶段删除现有 Job 或修改 Daily Pipeline；实现必须先完成需求冻结。
- 当前 `git status --short` 无输出，工作区无未提交变更。
- Jenkins 只负责参数、环境变量和 stage 编排；pytest 执行、失败 node id、重试和业务摘要必须保持在 `api-test/tools/ci_runner.py`，不得复制到 Groovy。
- 执行摘要和 Allure 产物需稳定落在 `api-test/runtime/ci-runs/<run_id>/`；Jenkins 与 DRF 均依赖该稳定契约。
- 后端仅通过 Jenkins API 触发或同步执行，前端仅通过 DRF API 展示；二者都不应拼接 pytest 或 Jenkins 执行命令。
- Jenkins 目录规则要求此类变更先完成需求说明、测试用例、架构影响评估，再修改 Pipeline；还需覆盖参数校验、执行模式选择、跨 Windows/Linux 分支和归档路径。

## 根因证据

- `jenkins/scripts/configure-local-mounted-jobs.groovy` 从 `api-test/utils/package_module.yaml` 读取模块，并为每个 `packageName` 构造 `${JENKINS_DAILY_FULL_JOB_PREFIX}-${packageName}` Job，同时为每个 Job 添加 `0 2 * * *` 定时器。
- 同一脚本会移除无后缀共享 Daily Job 的定时器，明确将旧共享 Job 作为历史保留，故 Jenkins 实际每日触发的是多个分模块 Job。
- `jenkins/scripts/daily-full-module-pipeline.groovy` 要求单一 `CASE_PATH`，通过 `JENKINS_MODULE_CASE_PATH` 执行一个模块，且代码注释和入口文件均声明“每个模块配置独立 Job”。
- `back-end/metrics/management/commands/sync_jenkins_job_bindings.py` 同样按 `${prefix}-${module.package_name}` 为每个模块创建 `daily_full` 绑定；同步任务再逐绑定向 Jenkins 发现构建。因此 Job 创建、执行和数据同步三个层面都固化为“每模块一个 Daily Job”。
- 现有 `jenkins/tests/test_pipeline_static.py` 和 `back-end/tests/test_metrics_commands.py` 正在断言上述旧模式，变更必须以新的契约测试替代旧断言。
- 独立调查确认模块清单当前由 `api-test/utils/package_module.yaml` 的 `test_gbif_case` 与 `test_gbif_case_module2` 提供；Stage12 实际初始化证据也记录两个子 Job 都有 timer、共享 Job timer 为 0。
- 当前 `api-test-pipeline.groovy` 的每次构建只产生一个 `RUN_ID`、一份 `summary.json` 和一套 Allure 结果；不存在 `parallel`、下游 `build job`、`waitForBuild`、并发上限或汇总屏障。解除 Jenkins 的禁止并发属性不等于限制全量模块执行为最多 10 并发。
- 后端的 `JenkinsJobBinding` 与 `JenkinsTask` 均关联单模块，任务发现/同步和模块快照落库均以绑定的单模块为前提；父任务是否需要持久化是数据模型关键决策。
- 当前 Jenkins 工具镜像仅显式安装 `allure-jenkins-plugin`，未声明可按任务类别限流并使超额构建排队的插件；Q8 的实现需要新增可验证的限流能力或采用等效、可持久化的 Jenkins 原生机制。
- `JenkinsTask` 和 `JenkinsJobBinding` 的 `module` 外键当前均为必填；Q2 的唯一 Daily 父任务要求引入不绑定单模块的父任务表达，同时保持模块快照、失败用例和执行历史从聚合产物逐模块更新。
- `api-test/tools/ci_runner.py` 当前一次只运行一个 `CASE_PATH`，并生成一份 summary 与一套 Allure 产物；Daily 父 Pipeline 必须在不复制 pytest 规则的前提下，为每个模块调度该统一执行器并生成父级聚合协议。
- 架构说明已把“每日全量 Job 执行全部模块”和“可选 Worker Job 承接拆分后的模块执行、最多 10 个任务限制”列为目标 Job 架构，故采用一个 Daily 父 Pipeline 调度受限模块执行符合既定方向。
- 需求模板要求冻结前明确：父 Job 与模块子结果的数据模型、状态机、报告入口、API 契约、权限、异常与并发语义；这些不能由实现阶段自行推断。

## 初步结论

根因不是 Jenkins 展示残留，而是当前架构刻意采用分模块 Job：init Groovy 负责创建与定时，Daily Groovy 只接受单模块 case path，后端绑定与发现也按模块 Job 运行。要达到目标，必须引入单一 Daily 入口的模块清单与并发调度/聚合协议，并把后端从“每模块发现一个 Job”改为“发现一个父 Job 后按模块结果同步”。

## 已冻结决策

- Q1：Daily、模块重试、失败重试三个 Pipeline 类型各自限制最多 10 个 Job 并发；配额不作为系统全局总上限，多个类型同时执行时总并发可以超过 10。
- Q2：Daily 全量执行在后端和前端只展示一个父任务；模块级执行结果不创建或展示子任务，只用于更新模块快照。
- Q3：Daily 仅提供父级聚合 Allure 报告；模块明细只保留为该构建的归档和汇总数据。模块重试与失败重试维持各自独立的报告与失败处理语义。
- Q4：新 Daily Pipeline 经最终验收后删除旧分模块 Daily Job；删除同时移除它们的 Jenkins 构建历史。该破坏性操作必须在最终验收门禁后执行。
- Q5：唯一 Daily Pipeline 固定每日 `02:00`；定时和手动触发都执行全部活跃模块，不提供模块子集选择；并发上限固定为 10。
- Q6：Daily 模块清单以 `api-test/utils/package_module.yaml` 为唯一权威来源；Jenkins 不访问后端数据库，后端只消费汇总结果更新模块快照。
- Q7：Daily 任一模块失败时，继续执行全部模块；待所有模块完成、结果汇总和聚合 Allure 归档后，父构建标记为失败。
- Q8：同一 Pipeline 类型达到 10 个并发 Job 时，新请求进入 Jenkins 队列等待该类型容量；不同类型的 10 并发配额互不占用。
- Q9：模块始终执行 YAML 全量；Daily 未传 URL 时使用当前私有配置默认值，Jenkins 支持传入 URL 参数覆盖为其他测试环境。现有 pytest 已支持 `--base-url` 覆盖及 URL 合法性校验，需求拟以 `TARGET_BASE_URL` 映射该能力。
- Q10：采用唯一 Daily 父 Job + 无定时 Daily Worker Job。Daily Worker 使用独立的 Daily 限流分类，最多同时执行 10 个 Job；父 Job 负责调度、等待、模块工件回收、汇总和父级 Allure。模块重试和失败重试各使用独立分类，各自最多 10 个 Job 并发。
- Q11：`TARGET_BASE_URL` 必须在现有 URL 校验后匹配已启用 `TestEnvironment.base_url`。未匹配时调度前失败，不创建父任务、不更新模块快照；避免无归属执行污染环境维度的审计、快照和趋势数据。
- 环境预检不能通过 Jenkins 直接读取数据库；若要在 Worker 调度前贯彻 Q11，需选择“Jenkins 调用后端只读预检 API”或维护第二份环境配置。后者引入漂移风险，运行后才拒绝则违背 Q11 的失败时机。
- Q12：采用 `api-test/utils/package_environment.yaml` 作为 Jenkins 调度前环境清单；顶层键映射后端 `TestEnvironment.env_key`，每项维护 `base_url`、`url_name`、`url_desc`。Jenkins 读取 YAML 且不访问数据库；后端同步 YAML 后使用同一环境标识关联任务、快照和审计。须用测试防止 YAML 与后端环境记录漂移。
- Q13：环境从 YAML 移除时，后端只标记 `TestEnvironment.is_active=false`，保留外键关联的历史任务、快照、趋势和审计。
- 新增范围：环境通过率页面支持环境 CRUD；平台写 MySQL 后同步 YAML，手工 YAML 修改后可从页面触发导入 MySQL。Compose 中 backend 镜像未挂载宿主机仓库，不能由 DRF 容器直接改 YAML；需由 Jenkins 受控工作区的专用配置同步 Job 写回。运行时 Git 提交/推送策略尚待主人确认。
- Q14：Jenkins 环境配置同步 Job 自动提交并推送受控主干。该 Job 必须在工作区干净、远端可快进时执行；若 Git 提交或推送失败，MySQL 保持已提交但标记为待同步，并返回可观察的结构化诊断。MySQL 与手工 YAML 同时变更的冲突处理尚待确认。
- Q15：以 `package_environment.yaml` 的 SHA 修订号作为 MySQL 写回前置条件。SHA 与记录值不一致时拒绝自动覆盖，管理员必须先导入 YAML 或基于最新 YAML 重新提交平台 CRUD，避免任何一方静默覆盖。
- 独立审查补充：环境配置同步 Job 不能写 `LOCAL_WORKSPACE_REPO` 的开发挂载目录，必须使用隔离且干净的 SCM checkout；SHA 使用 YAML Git blob SHA 而不是仓库 HEAD，避免无关提交造成伪冲突。当前硬编码 `seed_environment` 必须改为从随镜像复制的环境 YAML 建立初始 MySQL 投影。
- Task 2 独立审查确认 6 项阻断根因：Throttle Category 漏传节点/标签配额列表；Git SCM 的 `UserRemoteConfig` 凭据参数位置与 `GitSCM` 构造签名错误；旧分模块 Daily Job 的 TimerTrigger 未在升级时移除；Worker 复用共享 Allure 发布且缺少父构建来源验证；环境同步的 `merge-base` 祖先方向错误，可能在远端已领先时先写 YAML 和本地提交再于 push 失败。必须以先红后绿的 Jenkins 静态测试逐项关闭。
- Task 2 第二轮独立审查确认首轮修复仍有 4 项阻断：旧分模块 Job 手工构建会由共享 Daily 脚本重新写入 cron；同步请求标识、blob SHA 与 URL 参数可进入 shell；自由 URL 参数可携带服务令牌触发 SSRF；SCM checkout 后的裸 `git fetch/push` 不会复用 Jenkins Git 凭据。修复必须将服务端点固定为私有配置、严格校验调用参数、以独立最小权限 Git push 凭据包装 shell Git，并只由唯一父 Job 配置 cron。
- Task 2 第二轮安全修复与第三次独立审查已关闭全部阻断：父脚本按 `JENKINS_DAILY_FULL_JOB_NAME` 限定 cron；内部导出/回调端点只从私有服务基址加已校验请求 ID 构造；方向、请求 ID、blob SHA 在命令前严校验；checkout 与 fetch/push 凭据分离，后者以 askpass 临时环境作用域提供。真实 Jenkins 插件和凭据加载仍须由固定环境 Job 验收。

## 待调查

- 设计并验证可在现有 Jenkins 插件与版本化配置中实现“按类型独立、满额排队”的并发限流机制，并确认是否允许引入无定时 Worker Job。

## 2026-07-19 阶段 3 校准

- 功能测试用例共 27 条，RTM 已覆盖 AC1.1 至 AC4.2 共 18 条；后端与 Jenkins 实施必须以这些用例拆分 RED/GREEN 测试。
- UI 原型已冻结 R1-R4 页面、弹窗和权限映射；候选 C01-C05 均是同一功能范围的不同信息组织。主人未选择视觉基准前，不启动 Vue 编码或 Figma 正式稿。
- 需求原状态机曾将预检失败表示为已创建父任务的 `failed`，与 AC1.5“无父任务”的验收标准冲突。已将预检失败定义为 Jenkins 构建级诊断；只有预检成功后才创建平台父任务。
- `image_gen` 工具接口在当前环境不可用，UI 候选图为受控浏览器高保真渲染。该替代已记录在 UI 原型中，需主人在选择候选时一并确认。
