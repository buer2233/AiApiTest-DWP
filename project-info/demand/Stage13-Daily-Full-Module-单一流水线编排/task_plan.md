# Stage13-Daily-Full-Module-单一流水线编排：执行计划

## 目标

将 Daily 全模块执行收敛为唯一的 `AiApiTest-DWP-Daily-Full-Module` Jenkins Pipeline；该 Pipeline 每日调度当前全部模块，最多并发 10 个执行单元，并在同一契约内完成聚合、失败处理和 Allure 归档。

## 定级

M/L：涉及 Jenkins Job 创建策略、执行编排、并发协议、报告归档、后端同步和前端展示边界。不得裁剪需求、测试用例、UI、后端、前端、独立审查和验收阶段。

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 1. 现状与根因调查 | 已完成 | 已定位 Job 创建、Daily 执行和后端绑定均按模块拆分。 |
| 2. 需求澄清与规格冻结 | 已完成 | 主人于 2026-07-19 确认冻结；API 与架构边界可作为下游唯一输入。 |
| 3. 测试用例与 UI 设计 | 进行中 | 测试用例、RTM 与覆盖校准完成；UI 候选已产出，等待主人选择后生成正式稿。 |
| 4. 后端与 Jenkins TDD 实施 | 进行中 | Task 1/2/3 已完成；Task 4 API/结果同步及最终审查整改已完成，待独立审查。 |
| 5. 前端 TDD 实施 | 未开始 | 以冻结 API、UI 映射和 Playwright 用例为输入。 |
| 6. 独立审查、验证与验收包 | 未开始 | 执行回归，留存可提交的验收索引。 |

### 阶段 3 子任务

| 子任务 | 状态 | 输出边界 |
| --- | --- | --- |
| 3A 功能测试用例与 RTM | 已完成 | `project-info/test_case/Stage13-Daily-Full-Module-单一流水线编排/`，27 条用例覆盖 AC1.1-AC4.2。 |
| 3B UI 候选与交互映射 | 等待主人选择 | `project-info/UI/Stage13-Daily-Full-Module-单一流水线编排/`，5 张候选图、原型说明、区域语义拆解和实现映射已完成；待选定视觉基准。 |
| 3C 覆盖校准 | 已完成 | 已核对测试用例、UI 区域、API 契约与 RTM；前端仍须等待候选图选择和后端 API 实现。 |

### 后续实现任务

| 子任务 | 状态 | 依赖 |
| --- | --- | --- |
| 4A api-test 与 Jenkins TDD | 已完成 | Task 1/2 已完成三轮独立审查与静态回归；不触及后端/前端源码。 |
| 4B 后端数据模型与 API TDD | 已完成 | Task 4 API、结果同步与最终审查整改均已完成，待独立审查。 |
| 4C 后端/Jenkins 独立审查 | 进行中 | 4A、4B 已完成，等待最终对抗审查结论。 |
| 5A 前端 Playwright 与 Vue TDD | 未开始 | 3B 主人选定候选图、3C、4B API 已实现。 |
| 5B 前端独立审查 | 未开始 | 5A 已完成。 |

## 实施任务详情

### Task 1 api-test 环境目录与 Daily 聚合协议

**状态**：已完成。提交 `90febf5`、`b86f804`、`c254568`、`82ca312`；最终独立审查批准，任务回归 `90 passed`。

**所有权**：仅 `api-test/`（含其 pytest）；不得修改 `jenkins/`、`back-end/`、`front-end/` 或根配置。

1. 先增加失败 pytest，覆盖 `package_environment.yaml` 的 schema、URL 去尾斜杠、重复规范化 URL、未知字段、确定性 UTF-8 两空格序列化与 Git blob SHA 输入。
2. 新增环境目录解析/序列化的独立工具，复用 `config.validate_base_url`，只接受 `env_key -> {base_url, url_name, url_desc}`，不把凭据、数据库字段或运行状态写入 YAML。
3. 扩展统一 `ci_runner.py` 的请求与 pytest 命令，使 Worker 可将已校验的 `TARGET_BASE_URL` 作为现有 `--base-url` 传入；保持模块重试、失败重试与既有调用兼容。
4. 新增可测试的 Daily 聚合工具：读取模块清单，验证模块键唯一；汇总每个 Worker 的稳定摘要、模块明细和 Allure 原始结果到父运行目录；单模块测试失败不短路，缺失/重复/未知模块明细须给出结构化诊断。
5. 按 RED -> GREEN -> REFACTOR 留存命令和输出摘要；仅运行本任务 pytest 与必要既有 `test_ci_runner.py` 回归，不启动服务或生成可提交运行产物。

**完成条件**：TC-S13-F1-004、F1-005、F2-002、F2-004、F3-001、F3-002 对应的可执行 pytest 已先红后绿；接口约束可供 Jenkins 调用且没有复制 pytest/重试规则。

### Task 2 Jenkins 单一 Daily 编排与配置同步 Job

**状态**：已完成。提交 `8836e48`、`0f79125`、`b92d32c`；两轮整改后第三次独立复审批准。依赖 Task 1 已满足。

**所有权**：仅 `jenkins/`、Jenkins 相关 Docker/Compose 版本化配置及根 `.env.example`；不得修改 `api-test/`、`back-end/` 或 `front-end/`。

1. 先修改/增加 Jenkins 静态与 fake Jenkins 测试，验证唯一 Daily 父 Job 使用 `0 2 * * *`、无定时 Worker、遗留分模块 Job 在最终验收前不删除，以及 init 过程幂等。
2. 在版本化 Jenkins 插件和 init 配置中建立 Daily Worker、模块重试、失败重试三类独立限流分类，每类上限均为 10；超额构建必须由 Jenkins 队列等待。环境目录同步 Job 不计入三类配额且全局串行。
3. 将 Daily 父 Pipeline 改为读取 Task 1 的模块/环境预检和聚合协议，传入可选 `TARGET_BASE_URL`，为每个 YAML 模块触发无定时 Worker；等待所有 Worker 后才汇总、归档唯一父级 Allure 并决定父构建状态。
4. 增加专用环境目录配置同步 Job：使用隔离、干净 SCM checkout，按 expected YAML Git blob SHA 进行导出/导入，只有快进推送成功后回调；严禁写 `LOCAL_WORKSPACE_REPO`，不在 Groovy 复制 YAML 校验、pytest 或重试规则。
5. 同步更新 Jenkins 文档、`.env.example` 变量说明和静态门禁；不用本机绝对路径、固定端口或真实凭据。

**完成条件**：TC-S13-F1-001 至 F1-007、F3-005、F3-006、F4-001 的 Jenkins/static 断言先红后绿；旧 Job 删除守卫仅被实现为最终验收后的受控操作，不能在本任务执行删除。

### Task 3 后端环境目录数据模型与服务层

**状态**：已完成。提交 `8b2bbf4`、`de1aabe`、`4e18ab6`、`6f622e1`、`f7d79c9`；五轮 TDD 整改后最终独立复审批准。定向 pytest `51 passed`；全后端回归 `268 passed, 1 failed`，唯一失败为本任务前既有的固定日期趋势用例，未在本任务范围内修复。

**所有权**：仅 `back-end/`（模型、迁移、服务层、管理命令、pytest）；不得修改 Jenkins、api-test 或前端。

1. 先写 pytest-django 模型/服务测试，扩展 `TestEnvironment` 的 `url_desc`、规范化且全局唯一的 URL 与逻辑停用语义；系统始终至少保留一个启用环境，拒绝停用最后一项；新增目录状态单例和追加同步审计模型。
2. 通过 migration 完成约束升级；Daily `JenkinsTask.module` 与 `TestRun.module` 仅对 `daily_full` 允许为空，其他重试类型继续要求环境和模块。
3. 实现环境目录服务：原子创建同步请求、单一活动请求守卫、blob SHA 冲突拒绝、失败可重试、YAML 导入时新增/更新/停用但不物理删除，并确保无效导入零数据库副作用。
4. 将 `seed_environment` 改为从随镜像复制的环境 YAML 初始化投影，不能硬编码默认环境；运行时不能直接读写开发工作区 YAML。

**完成条件**：TC-S13-F2-001、F3-001 至 F3-012 的后端数据与服务行为先红后绿；测试使用 SQLite/fixture，不运行 migration 或容器服务。

### Task 4 后端 API 与 Jenkins 结果同步

**所有权**：仅 `back-end/`（DRF 路由、序列化/视图、Jenkins 同步与 pytest）；不得修改 Jenkins、api-test 或前端。

1. 先增加 DRF 测试，完整实现冻结的环境 CRUD、YAML 导入、同步状态读取与重试路径；所有写接口 admin-only，成功统一为 `{ "data": ... }` 和 `202`。
2. 增加受限内部 Jenkins 契约，用于读取冻结导出快照与回传导入/Git 结果；服务令牌、Git token 和原始内部 URL 不出现在浏览器响应或日志。
3. 修改 Jenkins Job binding 与结果同步：唯一 Daily 父构建映射为一条 module 为空的平台任务/运行；父摘要逐模块幂等更新快照、失败用例和趋势；预检失败构建不创建父任务。
4. 更新 Swagger/OpenAPI、已有管理命令测试和 `.env.example` 说明（仅当本任务新增配置变量）。

**完成条件**：TC-S13-F2-001 至 F2-004、F3-003 至 F3-013 的后端 API/同步行为先红后绿；无模块子任务 API、无直接 Jenkins/pytest shell 调用。

### Task 5 前端环境管理（等待主人选择 UI 候选）

**状态**：阻塞于主人选择 C01-C05 并确认浏览器高保真候选可作为 Figma 正式稿输入；不能提前编写 Vue 生产代码。

**所有权**：仅 `front-end/`（Playwright、Vue、Vitest）及 Stage13 UI 正式稿资料。实现时遵循 R1-R4 映射、冻结 API、`DESIGN-claude.md` 与 375/768/1024/1440px 状态矩阵。

### Task 6 独立审查、环境 Job 验证与验收

每项实现由独立 review agent 审查。后端、Jenkins 与前端均通过后，使用固定 Jenkins 环境 Job 进行环境验收，验收包只登记 Job/build、摘要和 artifact 名称；主人最终签字前绝不删除旧 Daily Job 或 Jenkins 构建历史。

## 约束

- AI 只能通过固定 Jenkins 环境 Job 进行应用环境操作，不能直接启动、停止、重建应用容器或安装依赖。
- 不删除现有 Daily Job，直到需求冻结、实现、验证和主人验收完成。
- 所有配置保持环境变量化，不引入主机路径、固定端口或真实凭据。
- 需求冻结前不得进入代码实现。

## 错误记录

| 错误 | 尝试 | 处理结果 |
| --- | --- | --- |
| Q7 规格回写补丁的非功能段落上下文不匹配 | 1 | 读取目标段落后使用精确上下文回写，未产生部分修改。 |
| Q9 跨文件规格回写补丁的调查记录上下文不匹配 | 1 | 改为按文件、按事实回写，避免跨文件补丁产生上下文耦合。 |
| Q11 跨文件规格回写补丁的进度文本上下文不匹配 | 1 | 未产生部分修改；已读取精确文本后重试。 |
| 读取不存在的 `back-end/.env.example` | 1 | 环境模板统一位于根 `.env.example`，后续不再读取模块级模板。 |
| 假定的环境页面文件和 `metrics/urls.py` 不存在 | 1 | 已确认路由集中在 `config/urls.py`；后续按实际前端目录定位，不重复使用假定路径。 |
| `django-tdd` 技能旧目录不存在 | 1 | 技能实际位于 `C:\Users\admin\.codex\skills\django-tdd`，已按正确目录读取。 |
| Task 2 审查包 Git Bash 路径错误 | 1 | 实际安装目录为 `D:\Program Files\Git\bin\bash.exe`，改用该目录生成只读审查包。 |
| 阶段 3 校准发现 AC1.5 与 Daily 父任务状态机冲突 | 1 | 以已冻结 AC1.5 为准，预检失败只保留 Jenkins 诊断，不创建平台父任务。 |
| 组合读取命令的 PowerShell 括号错误、图像查看的 `low` 细节参数无效 | 1 | 已拆分读取命令，并改用受支持的 `high` 图像查看；未改动业务文件。 |
| WSL `bash.exe` 不识别 Windows 路径，PowerShell `rg` 的 glob 参数顺序不兼容，以及假定 `config/settings.py` 存在 | 1 | 改用 `apply_patch` 写入 SDD 简报；后续 shell 搜索使用实际存在的路径和 PowerShell 兼容参数。 |
