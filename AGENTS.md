# AGENTS.md

本仓库是 `AiApiTest-DWP`，目标是建设一个面向 AI 协作、Jenkins CICD、DRF 后端、Vue 3 前端、Allure 报告展示的企业级自动化测试平台。项目采用 monorepo 单仓库结构，不拆分多个仓库。

## 核心交互规则

- 每次回复开头必须先叫我：主人
- 默认使用简体中文沟通。
- 开发过程中需要添加必要且清晰的简体中文注释。
- 不能把本项目当成无历史的新项目处理，必须保持多阶段开发上下文完整。

## 固定开发循环

每一个需求都是一次完整 loop，同一需求在不同阶段的产物命名必须一致，仅后缀不同，并能明确区分阶段。除非用户明确说明跳过，否则每次需求都必须包含以下产物和阶段。

### 1. 需求分析阶段

- 目录：`project-info/demand/`
- 产物：详细需求说明书（概要设计）。
- 要求：
  - 描述需求背景、目标、范围、不做事项和验收口径。
  - 每个功能必须说明能做什么、做到什么程度、满足什么要求。
  - 同步设计功能对应的数据表，包括字段、关联关系、更新规则和关键约束。
  - 必须补充架构影响评估，说明是否影响 DRF、Vue、Jenkins、`api-test`、Docker、数据模型、权限、报告协议和部署方式。
  - 涉及后端接口时必须输出 API 契约草案，包括资源路径、请求参数、响应字段、错误码、分页筛选、权限和关键状态流转。
  - 必须补充容器化兼容检查，确认是否存在本机绝对路径、宿主机固定端口、不可迁移配置或手工部署依赖。

### 2. 功能测试用例阶段

- 目录：`project-info/test_case/`
- 产物：详细功能测试用例（详细设计）。
- 要求：
  - 必须依据需求说明书编写。
  - 测试用例按模块和优先级组织。
  - 覆盖操作步骤、正常场景、异常场景、边界值和关键状态流转。

### 3. UI 原型图阶段

- 目录：`project-info/UI/`
- 产物：UI 原型图和交互说明。
- 要求：
  - 默认参考详细功能测试用例；如果需求说明书已经冻结角色、页面目标、核心字段、状态流转、权限边界和验收口径，可在测试用例编写期间并行输出第一版 UI 原型。
  - 并行输出的 UI 原型必须在功能测试用例完成后做覆盖校准，确认正常、异常、边界、权限和关键状态反馈没有遗漏。
  - 原型需要覆盖核心页面、弹窗、表格、筛选、状态和操作反馈。

### 4. 后端开发阶段

- 目录：`back-end/`
- 技术栈：Python、Django REST Framework、MySQL、pytest、pytest-django。
- 要求：
  - 必须依据需求文档和详细功能测试用例开发。
  - 先编写后端接口 pytest 测试用例，再开发接口，再回归测试。
  - 严格遵循 TDD：RED -> GREEN -> REFACTOR。

### 5. 前端开发阶段

- 目录：`front-end/`
- 技术栈：Vue 3、Vite、TypeScript、Element Plus、Vue Router、Pinia、Axios、TanStack Query for Vue、Vitest、Vue Test Utils、Playwright。
- 要求：
  - 必须依据 UI 原型图、后端接口、需求文档和功能测试用例开发。
  - 先编写 Playwright 自然语言 UI 自动化测试用例，再开发前端页面，再回归测试。
  - 仍按 TDD 流程推进。

## 非循环基础阶段

以下内容属于平台基础设施建设，不要求每个需求都重复产出；需要调整时按实际工作需求执行。

- `docker/`：容器设计、Docker Compose、基础服务部署说明。
- `jenkins/`：Jenkins Pipeline、Groovy 脚本、Job 模板和执行归档策略。

后期平台必须支持作为一个 Docker Compose 项目整体打包部署。后续任何后端、前端、Jenkins、`api-test` 执行器和报告入口设计，都必须避免绑定个人本机路径、宿主机固定端口或不可迁移环境，保证可以通过环境变量、Compose 服务名、volume 和标准镜像构建方式迁移到整体容器化部署。

## 流程检查点和并行规则

固定 loop 保持阶段产物完整和命名一致，但不要求所有阶段机械串行。满足输入完整、边界清晰、产物可汇合时，可以使用 subagent 并行推进独立阶段。

必须设置以下检查点：

- 架构影响评估：需求分析阶段完成，判断是否影响模块边界、数据模型、Jenkins 执行链路、报告协议、权限、安全或 Docker 化部署。
- API 契约冻结：后端开发前完成，冻结 DRF API 路径、请求、响应、错误码、分页筛选、权限和状态流转；前端开发必须依据已确认契约。
- 容器化兼容检查：需求分析、后端开发、前端开发、Jenkins/Docker 变更和联调验收都要检查，避免写死本机路径、宿主机端口、真实凭据或不可复现手工配置。

允许的并行方式：

- 需求说明书完成并通过架构影响评估后，可以并行启动“功能测试用例设计”和“UI 原型设计”。
- UI 原型可以先依据需求说明书输出第一版，但必须在功能测试用例完成后进行覆盖校准。
- 后端开发必须等待功能测试用例和 API 契约冻结，不因 UI 原型提前完成而提前编码。
- 前端开发必须等待 UI 原型、功能测试用例和后端 API 契约完成。
- 使用 subagent 时，主 agent 负责提供完整输入、限定输出文件、汇总冲突、执行最终一致性检查；不得让多个 subagent 同时编辑同一文件。

## 项目基础架构

- `api-test/`：接口自动化执行核心，维护 pytest 用例、接口方法、失败 node id、重试执行器和 Allure 原始结果。测试执行协议只在此处实现。
- `jenkins/`：严格执行主干。平台侧所有测试执行、模块重试、失败重试和报告生成都必须通过 Jenkins。
- `back-end/`：DRF 平台编排和数据中心，负责用户、权限、任务、模块快照、失败用例、Jenkins 触发/同步、报告入口和审计。
- `front-end/`：Vue 3 企业级管理后台，负责模块通过率、失败用例、Jenkins 任务、报告入口和平台操作体验。
- `docker/`：当前维护本地 MySQL、Jenkins 等基础服务，后期承载整个平台 Docker Compose 打包部署方案。
- `project-info/`：项目资料，不存放业务实现代码或运行产物。
- `docs/`：额外说明文档。

详细架构以 `project-info/project_detail/project-architecture.md` 为准。

## 全局技能推荐

必须优先使用：

- `/using-superpowers`
- `/planning-with-files`

全局推荐：

- `brainstorming`：新需求、新功能、架构和行为变更前使用。
- `product-requirements`：需求分析和 PRD 编写时使用。
- `test-driven-development`：所有开发阶段遵循 TDD。
- `systematic-debugging`：遇到问题、失败或异常行为时使用。
- `receiving-code-review`：处理代码审查意见时使用。
- `drawio-skill`：架构图、流程图、ER 图等可视化资料使用。
- `subagent-driven-development`：需求阶段完成且任务边界独立时，用于并行推进测试设计、UI 原型、独立实现和审查任务。

模块技能：

- 后端：`django-tdd`、`api-design`、`python-patterns`、`python-testing`
- 前端：`vue-best-practices`、`frontend-design`、`vue-router-best-practices`、`vue-pinia-best-practices`、`vue-testing-best-practices`
- 设计：`ui-ux-pro-max`、`ckm:design-system`

## 安全规范

- 不提交真实账号、密码、token、cookie、租户密钥、Jenkins API Token、生产 URL 或敏感地址。
- 示例配置必须使用占位符、环境变量或本地私有配置。
- `.env`、报告、日志、抓包、运行时产物不得作为业务代码提交。
- Jenkins、DRF、Vue 和 pytest 中都保持平台字段通用，不引入不可迁移的业务常量。

## 协作规则

- 根目录 `AGENTS.md` 只维护全局流程、架构、技能、安全和模块边界。
- 子目录 `AGENTS.md` 维护各模块技术栈、命令和目录约定。
- `CLAUDE.md` 只保留 `@AGENTS.md` 引用，不复制规则。
- 每一个需求loop循环都需要单独 `git commit` 和 `git push`，并写明详细的提交备注信息。

## 按需参考

- Docker 部署：`docker/DEPLOYMENT.md`
- 架构说明书：`project-info/project_detail/project-architecture.md`
- LLM 编码准则：`andrej-karpathy-skills.md`
