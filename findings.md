# 开发流程与架构重构发现记录

## 2026-06-28 第一个需求：用户登录注册和测试用例展示

- 用户提出第一个需求：先实现用户登录、注册和测试用例展示。
- 按根 `AGENTS.md` 的需求分级，本需求初判为 M 档：涉及 DRF 后端、Vue 前端、用户权限、测试用例数据模型、API 契约和页面，完整 loop 不裁剪任何阶段。
- 当前仓库已有完整开发流程、需求说明书模板、RTM/验收包模板、架构说明和 Docker 化约束，不能跳过需求澄清冻结、架构影响评估、API 契约冻结和容器化兼容检查。
- `progress.md` 历史记录显示 2026-06-28 曾启动服务并验证登录、注册、测试用例展示，但当前 Git 可维护源码缺失，不能把运行缓存当作正式实现。
- `back-end/` 下存在 `apps/`、`common/`、`config/`、`tests/` 目录，但递归检查只看到 `__pycache__` 与 `.pyc`，没有 `.py` 源码；后端需要重新创建 Django/DRF 源码、测试、迁移和配置文件。
- `front-end/` 下存在 `tests/screenshots/01-login.png`、`02-register.png`、`03-testcases.png`，但缺少 `package.json`、`src/`、Vite 配置和 Playwright 测试源码；前端需要重新创建 Vue 3 工程源文件和测试。
- `.gitignore` 忽略 `front-end/node_modules/`、`front-end/dist/` 和根 `/tests/`，但没有忽略 `back-end/apps/`；后端源码缺失不是正常忽略导致。
- `api-test/test_case/` 已有测试用例模块目录，可作为测试用例展示的数据来源候选；是否“扫描文件同步入库”仍需主人确认。
- 架构要求 DRF 后端不直接执行 pytest；本需求的“测试用例展示”应只做用例元数据读取/展示，不触发 Jenkins 执行链路，除非主人扩大范围。
- 主人已裁决首期方案：注册后默认 active、使用 DRF Token、后端扫描 `api-test/test_case/` 同步入库、注册需要邀请码、测试用例展示完整首期字段、admin 可同步而 member 只读。
- 主人已裁决 Q7=B：邀请码采用数据库表和后台管理能力。首期最小范围为 admin 创建、查看、禁用邀请码；邀请码支持最大使用次数和过期时间；注册成功后累计使用次数。
- Q7=B 使首期范围扩大：新增 `registration_invite_code` 表、邀请码管理页面 `/invite-codes`、邀请码创建/列表/禁用 API，以及 admin/member 权限差异测试。
- 后端 RED 证据已确认：缺少 `config.settings.test` 和 `manage.py` 是预期失败点，说明测试确实先于生产代码暴露缺失实现。
- 后端实现采用仓库相对扫描路径：默认从 `REPO_ROOT / api-test / test_case` 解析 pytest 用例，并保存 `api-test/test_case/...` 形式的相对路径，未引入本机绝对路径或 Jenkins 执行行为。
- DRF 响应统一为成功 `{ data, meta? }` 和错误 `{ error: { code, message, details? } }`，与冻结 API 契约保持一致。
- 后端 GREEN 证据已确认：`18 passed`，`apps + common` 覆盖率 `94%`。
- 独立前端审查发现并已修复：管理员路由守卫未等待 `auth/me`、邀请码禁用 UI 缺失、列表分页缺失、测试用例类名列缺失、401 失效登录态处理缺失、注册字段级错误缺失、Vite proxy 默认 localhost 与容器化约束冲突、`src/**/*.js` sidecar 运行产物误入源码目录。
- 独立后端审查发现并已修复：注册唯一约束并发冲突未转业务错误、过期邀请码状态回滚、同步源缺失状态码不符、非法 `sync_status` 未校验、无效 Token 错误码不统一、Allure 标题解析优先级错误、邀请码数据库 CheckConstraint 缺失。

## 2026-06-26

- 当前工作区初始状态干净，最近提交包含“清理回退现有的开发内容”和项目说明结构优化。
- 根目录 `AGENTS.md` 当前包含较完整的项目定位、模块边界、安全规则、技能推荐和 Git 规则，但用户希望进一步简约化。
- 根目录 `README.md` 当前非常简短，只说明项目是面向 AI 协作的 CICD 自动化测试平台。
- `api-test/AGENTS.md` 明确接口自动化执行核心基于 pytest、requests、allure-pytest，并已有 `tools/ci_runner.py` 作为 Jenkins 和 DRF 后端统一调用入口的约定。
- `back-end/AGENTS.md` 固定为 Django REST Framework，职责包含用户角色、测试任务、失败用例、报告入口、Jenkins 查询和触发 API。
- `front-end/AGENTS.md` 当前仍写 Vue 3 + Vite + TypeScript + Element Plus，但上次任务已清空前端代码，仅保留规则文件，因此前端技术栈可重新评估。
- `jenkins/AGENTS.md` 当前定位为 Pipeline 参数、stage 编排、跨平台 agent、调用 `api-test/tools/ci_runner.py`、归档和发布 Allure 报告。
- 用户提出关键架构问题：如果所有模块都在一个项目内，后端是否可以直接执行用例和重试，避免 Jenkins 再转发一次。
- `back-end/` 当前没有 DRF 业务代码，仅有协作规则文件、`__pycache__` 和 `.pytest_cache`；快速启动文档里描述的后端已不存在。
- `front-end/` 当前没有前端业务代码，仅有 `AGENTS.md` 与 `CLAUDE.md`；快速启动文档里描述的 Vue 3 前端已不存在。
- `docker-compose.yml` 当前只启动 MySQL 与 Jenkins，不包含后端、前端或 `api-test` 应用容器。
- `api-test` 已有较清晰的执行器资产：`tools/ci_runner.py`、pytest node id 收集、失败重试、Allure 产物目录和自身测试。
- `jenkins` 已有 Groovy Pipeline 与静态测试资产，但其 README 仍写“Stage 4 已实现”，后续可保留为可选 CI 集成入口，而不是平台内部执行的唯一入口。
- 用户倾向保留 Jenkins 作为企业流水线执行入口，并认为全部统一走 Jenkins 可能更规范、扩展性更高。
- 初步判断：统一走 Jenkins 可以作为执行主干，但不能让 DRF 退化为简单转发器；DRF 仍应负责测试任务建模、权限、审计、调度记录、失败用例归档、报告索引和前端 API。
- 用户确认平台执行必须 100% 依赖 Jenkins 可用，所有测试都通过 Jenkins 执行。
- 用户确认当前 `api-test` 测试框架基本稳定，重试或报告展示相关变更应单独改动测试框架，不在后端或 Jenkins 中重复实现。
- 用户提供目标页面参考：模块通过率列表展示环境、模块、用例包名、模块名、负责人、自动化负责人、通过率、运行日期、运行时间和操作按钮。
- 用户要求每天凌晨 1 点自动执行现有所有测试用例，执行结果作为当天最新测试数据展示在平台上。
- `api-test/test_case/` 下每个子文件夹代表一个模块，例如 `test_case/test_gbif_case`。
- 用户要求两类重试独立执行：模块重试重跑整个模块并更新该模块“日期”和“执行时间”；失败重试只执行当前模块失败用例，通过率 100% 时提示无需失败重试，且不更新模块“日期”和“执行时间”。
- 用户要求模块重试 Job 和失败重试 Job 独立，且一个 Job 下最多允许 10 个任务同时执行。
- 用户要求模块级互斥：同一模块无论正在执行失败重试还是模块重试，都不允许再触发另一种重试。
- 用户要求平台具备 Jenkins 任务状态查看和操作能力，参考截图中的取消任务、查看报告、查看 Jenkins 任务、标记失败、查看进度等操作。
- 用户要求点击模块通过率时展示失败用例明细，包含用例名、描述、错误类型、断言、执行状态、错误信息、确认结果以及 Jenkins 任务/测试账号等操作。
- 用户确认失败重试执行成功后，主表的通过率、失败数、成功数也需要更新；但仍沿用此前约束：失败重试不更新主表“日期”和“执行时间”。
- 第一张主表是模块展示快照表：模块条数固定，每个模块一条当前展示数据；每日全量、模块重试、失败重试完成后按规则更新对应模块行。
- 第二张表是失败记录表：记录当前模块当天失败用例，字段需支持用例描述、pytest node id、错误类型、错误信息、确认结果、关联缺陷和重试状态。
- 第三张表是 Jenkins 执行记录表：记录 env、任务类型、case_id、Jenkins job/build URL、状态、任务名，并支持分页查询和前端操作。
- 用户提供的接口样例包含内网地址、环境 URL 和业务用例文本，正式文档需要抽象为通用测试平台字段，不能固化真实环境地址或业务常量。
- 前端技术栈评估结论：当前项目是典型企业级测试管理后台，核心页面以筛选、表格、弹窗、任务状态、报告入口和高频操作为主；推荐继续使用 Vue 3 + Vite + TypeScript + Element Plus，并补充 Pinia、Vue Router、Axios、TanStack Query、Vitest、Vue Test Utils、Playwright。
- React + Ant Design Pro/Next.js 适合已有 React 团队或需要全栈 React/SSR 的项目，但本项目 DRF 后端已固定，SSR 和 React 全栈能力不是核心收益。
- Angular 适合大型强约束团队，但对当前项目和 AI 快速迭代成本偏高。

## 2026-06-27 整体 Docker 化架构增强

- 用户要求将后期整个平台通过 Docker 打包部署的预案写入 `docker/AGENTS.md`，并在 `docker/` 新增 `CLAUDE.md`。
- 用户要求全局 `AGENTS.md` 与 `project-info/project_detail/AGENTS.md` 明确：后续设计和开发都必须满足整体 Docker 化部署能力。
- 当前架构说明书仍写“Docker 负责基础服务，不默认把业务应用全部容器化”，需要改为“当前阶段默认基础服务，后期必须支持 Compose 编排整个平台”。
- 推荐整体 Docker 化形态不是单一大镜像，而是一个 Docker Compose 项目编排 `mysql`、`jenkins`、`backend`、`frontend`、`nginx`、`api-runner` 或 Jenkins agent 等服务。
- 后期容器化关键约束：服务间使用 Compose 服务名通信，不能写死 `127.0.0.1`、个人机器路径或宿主机端口；凭据通过环境变量、Jenkins Credentials 或本地私有配置注入。
- `api-test` 更适合以 Jenkins agent 或 runner 镜像形式执行，不建议作为长期常驻 Web 服务；Jenkins controller 负责编排，runner 负责 pytest、Allure 和执行产物。

## 2026-06-27 开发流程检查点与 subagent 并行评估

- 当前固定 loop 的优点是阶段产物完整、可追溯，适合企业级测试平台；不足是 UI 原型强依赖详细测试用例会拉长前置等待时间。
- 需求说明书如果足够完整，UI 设计可以直接参考需求说明书并行输出第一版原型；详细测试用例完成后再做 UI 覆盖校准。
- 功能测试用例设计和 UI 原型设计适合使用两个 subagent 并行处理，但必须由主 agent 维护同一需求命名、输入文档和汇合检查。
- 后端开发适合在功能测试用例和 API 契约冻结后启动，不能因为 UI 原型先完成而提前进入后端编码。
- 前端开发适合在 UI 原型和后端 API 契约都完成后启动；Playwright 自然语言测试需要同时参考 UI 原型和功能测试用例。
- 三个新增检查点应落在需求说明书和联调验收中：架构影响评估、API 契约冻结、容器化兼容检查。
