# Findings & Decisions

## Requirements
- 当前框架已有完整接口自动化结构，可通过 AI 编写接口方法和 pytest 用例。
- 已有可执行 demo，可生成 Allure 测试报告。
- 需要在现有框架结构基础上增加 CICD 能力。
- 需要在网页端测试平台实现执行用例、错误重试、测试报告展示、Jenkins 执行查询等功能。
- 用户要求先一起头脑风暴并反复对接需求，直到需求确认通过，再使用 TDD 模式开发。
- 项目必须保持通用接口自动化框架定位，不绑定具体业务系统，不引入真实账号、cookie、token 或业务常量。
- 前端使用 Vue 3，目录为 `front-end/`。
- 后端使用 Python DRF，目录为 `back-end/`。
- 现有接口自动化测试框架需要迁移到 `api-test/`，包含 `report/`、`test_case/`、`test_data/`、`utils/`、`config.py`、`conftest.py`、`pytest.ini`、`requirements.txt`、`runpytest.py`。
- 迁移后必须执行 `runpytest.py` 验证路径处理和运行能力未受影响。
- Jenkins 第一阶段必须实现，目录为 `jenkins/`，通过 Groovy 脚本调用本地接口自动化测试、失败重试、Allure 报告生成等能力。
- 失败重试需要支持选择一个或多个失败用例重试、一键重跑全部失败用例、按模块重试，模块通过测试用例文件夹区分。
- 失败用例重试通过组合 pytest 用例 ID 进行重跑。
- Web 平台需要展示每条失败用例的简要信息，并支持点击打开 Allure 报告。
- 平台需要用户登录和权限，先保留管理员和普通用户两类角色，当前权限可以一致，但模型要预留后续差异化权限空间。
- 截图是参考设计，不要求完整照搬。
- 这是大型任务，需要分 10 个阶段开发，每个阶段都必须执行完整 TDD 流程，开发计划文档要持续记录阶段、任务和进度。
- 每个阶段必须单独完成：需求分析、编写测试用例、开发、测试。
- 每个阶段开发和测试完成后，必须单独执行 `git commit` 和 `git push`。
- DRF 认证使用 DRF Token。
- 后端数据库默认直接使用本地 MySQL。
- 前端组件库使用 Element Plus。
- Jenkins 查询与触发 API 阶段要确认 Windows 和 Linux 兼容；脚本源文件存放在 `jenkins/` 并通过 git 管理。
- Allure 报告展示方式确认打开静态 HTML 报告。
- 开发和测试中产生的文档全部记录在 `docs/`。

## Research Findings
- 根目录没有 `.codegraph/`，后续代码理解直接使用 `rg` 和文件读取。
- 项目已有 `runpytest.py`、`conftest.py`、`config.py`、`test_case/page_api/`、`test_case/test_gbif_case/`、`report/` 等结构。
- 根目录已有上一轮任务的规划文件，本轮已替换为 CICD + 测试平台需求设计计划。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 需求阶段先不写实现代码 | 用户要求需求确认后才进入 TDD 开发 |
| 设计时将 Jenkins 能力抽象为可替换集成 | 便于本地测试、模拟 Jenkins、未来对接真实 Jenkins |
| 把平台功能拆成任务编排、执行器、报告、CICD 集成、前端展示几个域 | 降低复杂度，便于测试和渐进交付 |
| 每阶段完成后单独 commit 和 push | 满足用户对阶段边界和版本管理的要求 |
| 后端默认本地 MySQL，不再使用 SQLite 作为默认数据库 | 用户已明确指定数据库方案 |
| `AGENTS.md` 和 `README.md` 必须先反映 CICD 平台定位 | 这两个文件是后续 AI 和工程师最容易先读到的入口，必须避免继续传递旧的单体接口自动化框架定位 |
| Stage 3 将 pytest node id 与 CI 执行能力放入 `api-test/tools/` | Jenkins Groovy 和 DRF 后端后续只调用统一工具，避免两处重复拼接 pytest 和重试逻辑 |
| `all-failed` 模式读取 `.pytest_cache/v/cache/lastfailed` | 该文件是 pytest 原生失败 node id 来源，能保留原始 node id 字符串 |
| 执行器在本次 pytest 运行前清理旧 `lastfailed` cache | 避免上一次失败用例污染本次成功运行的 `failed_nodeids.json` 和 `summary.json` |
| `retry_count` 不允许为负数 | Jenkins/后端传参错误时应尽早失败，不生成语义不清的 pytest 命令 |
| AGENTS 采用根目录总规则 + 子目录模块规则分层 | 根目录维护全局阶段流程和安全规则，`api-test/`、`back-end/`、`front-end/`、`jenkins/` 分别维护模块约定，`CLAUDE.md` 只引用同级 `AGENTS.md` |
| Jenkins 参数通过环境变量传递给 `ci_runner` | Groovy 只负责参数和 stage 编排，pytest 目标解析、node id 拆分、重试和 summary 继续集中在 `api-test/tools/ci_runner.py` |
| `PYTEST_NODE_IDS` 支持换行和英文逗号 | Jenkins text 参数便于人工粘贴多个 pytest node id，Python 执行器负责去空和去重 |
| Jenkins `Run API Tests` 使用 `catchError` | pytest 失败时仍要执行归档和 Allure 发布，否则失败 node id 和 summary 无法在构建页查看 |
| Stage 5 所有环境强制使用本地 MySQL `localhost:3306` | 满足用户明确要求，避免 pytest 或运行环境回退 SQLite，也避免通过环境变量切到非本地主机端口 |
| `accounts.User` 继承 Django `AbstractUser` 并只新增 `role` | 保留 Django username/password/session/admin 基础能力，最小化 Stage 5 实现面 |
| `create_superuser()` 默认写入 `role=admin` | 保证命令行创建管理员时角色正确；普通用户默认仍为 `member` |
| Stage 6 `test_runs` app 只适配 `api-test/tools/ci_runner.py` | 后端不复制 pytest 命令、node id 解析或重试规则，避免和 Jenkins 分叉 |
| Stage 6 失败用例优先从 Allure result JSON 解析，缺失时回退 `summary.failed_nodeids` | 兼顾报告摘要丰富度和执行器最小输出 |
| Stage 6 报告入口返回 `/reports/<run_id>/` 而不是服务器路径 | 避免泄露本机绝对路径；静态报告服务留到 Stage 10 |
| Stage 7 Jenkins 凭据只从环境变量/Django settings 读取 | 避免提交真实 Jenkins URL、用户名或 API token |
| Stage 7 Jenkins trigger API 输出 Stage 4 Pipeline 参数名 | `CASE_PATH`、`PYTEST_NODE_IDS`、`RETRY_MODE`、`RETRY_COUNT`、`CLEAN_ALLURE`、`OPEN_REPORT` 保持跨模块一致 |
| Stage 7 Jenkins client 支持 fake session 注入 | client 单测不依赖真实 Jenkins 服务或网络 |
| Stage 8 前端使用 getdesign Claude `DESIGN.md` 作为设计参考 | 用户明确要求参考 `https://getdesign.md/claude/design-md`，并执行 `npx getdesign@latest add claude` |
| Stage 8 登录态本地持久化为 `auth.token` 和 `auth.user` | 支持刷新后保持平台壳访问，并让 Axios 拦截器统一追加 DRF Token |
| Stage 8 路由守卫通过 `createPlatformRouter()` 统一生产和测试入口 | 确保 Vitest 验证真实守卫行为，而不是仅验证静态路由数组 |
| Stage 8 平台布局只放静态入口和占位卡片 | 遵守阶段边界，模块通过率表格和失败用例弹窗留到 Stage 9 |
| Stage 8 Vite dev server 需要代理 `/api` 到 `http://127.0.0.1:8000` | 前端 Axios 默认 baseURL 为 `/api`，没有代理时浏览器请求会落到 Vite 自身并返回 404 |
| Docker Compose 统一 MySQL 和 Jenkins 两个服务 | 使用根目录 `docker-compose.yml` 管理 `mysql:8.4` 和 `jenkins/jenkins:lts-jdk17`，保留与现有容器一致的容器名、数据卷和默认端口，`.env` 本地化配置且不入库 |
| Jenkins 工具链镜像作为可选 override | 默认 Compose 优先快速拉起官方 Jenkins；需要容器内直接执行 pytest/Allure 时，再用 `docker-compose.jenkins-tools.yml` 构建带 Python、git、Allure CLI 的镜像，避免一键部署被外网下载阻塞 |
| `project-info/` 用于项目说明资料和架构图 | 该目录只沉淀架构图、架构说明书、执行流程图等交接资料，不放业务实现代码、运行产物或敏感配置 |
| 项目架构图同时保留原始生成图和 4K 放大图 | 内置图像生成工具实际输出约 `1672x941`，已复制到 `project-info/project-architecture.png`，并额外生成 `3840x2160` 的 `project-info/project-architecture-4k.png` 作为交付查看版本 |
| Stage 9 前端直接适配 Stage 6 `test_runs` API | 模块通过率、失败用例弹窗、选择重试、一键失败重试、模块重试和报告入口复用后端既有契约 |
| Stage 9 使用测试专用 Element Plus stub | `el-table`/`el-select` 在 jsdom 中出现递归更新；stub 保留文本渲染、v-model、按钮点击和 row slot 行为，业务代码仍用真实 Element Plus |
| Stage 9 保持 Claude 风格的操作台界面 | 深色模块页头、奶油指标卡、紧凑筛选条和表格，避免营销页或装饰性卡片堆叠 |
| `frontend-patterns` 技能当前环境不可用 | 已通过技能列表、文件搜索和延迟工具搜索确认未找到，Stage 9 以现有 Vue/Element Plus 项目模式补位 |
| Stage 10 Allure 报告服务只允许 `ALLURE_REPORTS_ROOT` 内路径 | 后端返回 `/reports/<run_id>/` 前会确认 `report_path/index.html` 存在，且 `report_path` 位于配置根目录下，避免泄露任意本地目录 |
| Stage 10 前端报告入口继续复用 `GET /api/test-runs/{id}/report/` | 保持 Stage 6/9 已建立的接口契约，模块表格和失败弹窗都打开后端返回的受控 URL |
| 后端注释补齐不改变业务行为 | 本次只新增文件级、类级、方法级和关键步骤注释；`compileall`、Django check、迁移检查和后端 34 条测试均通过 |

## Documentation Alignment
- 2026-06-22 17:54:17 +08:00：已将 `AGENTS.md` 更新为 CICD AI 自动化测试平台的后续 AI 接手规则，明确必须读取主计划、`task_plan.md`、`findings.md`、`progress.md`、`README.md` 后再继续开发。
- 2026-06-22 17:54:17 +08:00：已将 `README.md` 更新为平台总览，包含 `api-test/`、`jenkins/`、`back-end/`、`front-end/`、`docs/` 的职责，10 阶段主计划和当前 `api-test` 运行入口。
- 当前工作区显示 `api-test/` 已存在迁移内容，根目录旧接口框架文件处于删除状态；后续继续 Stage 2 前必须核对迁移测试和实际验收结果，不能仅凭目录存在标记完成。

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 规划文件已有旧任务内容 | 已替换为当前任务计划，并在进度中记录 |
| Stage 3 初始测试无法导入 `tools` 包 | 按 TDD 创建 `api-test/tools/__init__.py`、`pytest_nodeids.py` 和 `ci_runner.py` |
| 旧 pytest `lastfailed` cache 会污染当前运行结果 | 增加测试并在执行器运行前清理旧 cache |
| 根目录和子目录协作规则容易重复维护 | 统一要求所有 `CLAUDE.md` 只写 `@AGENTS.md`，实际规则只维护在同级 `AGENTS.md` |
| Stage 4 初始测试无法找到 Jenkins env 适配函数 | 先写失败测试，再新增 Jenkins env 到 `RunRequest` 的转换入口 |
| Stage 4 初始 Jenkins 静态测试找不到 Pipeline 文件 | 创建 `jenkins/Jenkinsfile` 和 `jenkins/scripts/api-test-pipeline.groovy` |
| Stage 4 发现 pytest 失败会阻断归档 | 增加补强测试并用 `catchError` 保留后续归档阶段 |
| Stage 5 初始账户测试无法收集 | 创建 Django settings、urls、accounts app 和 pytest 配置后解决 |
| Stage 5 当前环境缺少 `pytest-django` | 执行 `python -m pip install -r back-end/requirements.txt` 补齐依赖 |
| Stage 5 `create_superuser()` 初始默认 role 为 `member` | 增加自定义 `UserManager` 和 manager 迁移，补强测试转绿 |
| Stage 5 本机默认 MySQL 数据库不存在 | `docs/back-end-accounts.md` 记录 `CREATE DATABASE` 和迁移命令 |
| Stage 5 pytest 下仍回退 SQLite | 增加数据库配置测试后删除 SQLite 分支，固定 MySQL `localhost:3306` |
| Stage 6 初始测试无法导入 `apps.test_runs` | 按 TDD 创建 `test_runs` app、模型、服务、序列化器、视图和 URL |
| Stage 6 MySQL 拒绝 `(test_run, node_id)` 唯一索引 | pytest node id 可能很长，移除该唯一约束，保留完整 node id 字段 |
| Stage 6 首次失败迁移污染复用测试库 | 使用 `--create-db` 重建 MySQL 测试库后验证通过 |
| Stage 5 文档与当前配置存在端口不一致 | 文档/计划写 `localhost:3306`，当前 `settings.py` 和测试断言为 `3307`；本轮未扩大修改范围，后续应单独校准 |
| Stage 7 初始测试无法导入 `apps.jenkins_integration` | 按 TDD 创建 Jenkins 集成 app、client、API、迁移和配置入口 |
| Stage 8 初始前端测试无法解析 `@/api/auth` | 确认 RED 后创建 Vue 3 工程、认证 API、Pinia store、路由和布局 |
| Stage 8 构建缺少 Node/Vite 类型与第三方声明检查失败 | 添加 `@types/node`、`vite/client`，并启用 `skipLibCheck` 处理依赖声明噪声 |
| Stage 8 窄桌面平台卡片标题被指标网格挤压 | 提高响应式断点，让平台卡片在内容宽度不足时改为单列 |
| Stage 8 完整依赖树审计有开发依赖漏洞提示 | `npm audit --omit=dev` 为 0 vulnerabilities；本阶段不使用 `npm audit fix --force` |
| 前端登录请求 `admin/admin` 报错 | Vite 代理修复后该请求返回 400，原因是 DRF 测试管理员密码为 `admin123456`，不是 Jenkins 管理员密码 `admin` |
| Jenkins 工具链镜像构建超时 | 默认 Compose 改为官方 Jenkins 镜像快速启动，保留 `docker-compose.jenkins-tools.yml` 作为可选工具链镜像 |
| 用户消息中写作 `AGENGT.md` | 按仓库既有分层规则理解为 `AGENTS.md`，已在 `project-info/` 创建 `AGENTS.md`，并让同级 `CLAUDE.md` 仅引用 `@AGENTS.md` |
| Stage 9 初始前端测试无法解析 `@/api/testRuns` | 确认 RED 后创建测试任务 API 封装、模块页面、表格、筛选和失败用例弹窗 |
| Element Plus 表格和选择器在 jsdom 中递归更新 | 前端测试改用轻量 stub，避免测试环境测量/teleport 噪声；Playwright 仍验证真实 Element Plus 渲染 |
| Stage 10 报告 API 缺少真实 `index.html` 校验 | 增加 RED 测试后实现 `_report_index_exists()`，缺失报告首页时返回 404 |
| Stage 10 `/reports/<run_id>/` 没有静态路由 | 增加 RED 测试后实现 `serve_allure_report()` 并挂载报告首页和资源路径 |
| Stage 10 报告路径需要避免任意目录暴露 | 增加 `ALLURE_REPORTS_ROOT` 和根目录约束测试，根目录外报告路径返回 404 |
| Stage 10 api-test 回归因本地 PyCharm 配置缺少 `api-test/runpytest.py` 配置失败 | 该文件是未跟踪 IDE 状态；已本地恢复运行配置用于满足现有本地测试，不纳入 Stage 10 提交 |
| 后端注释补齐需要覆盖测试和迁移文件 | 已逐个直接读取 `back-end` 下 Python 文件，并为业务代码、配置、迁移、测试和包初始化文件添加对应说明 |

## Resources
- `AGENTS.md`
- `runpytest.py`
- `conftest.py`
- `config.py`
- `test_case/page_api/public/base_api.py`

## Visual/Browser Findings
- 参考图 1：模块通过率列表页包含顶部导航、左侧菜单、筛选区、模块/库类型页签、模块表格、通过率、运行时间，以及“一键失败重试”“模块重试”“更多”菜单；更多菜单含近 7 天、近 30 天、上传报告、Jenkins 任务、环境比对、作废等入口。
- 参考图 2：失败用例弹窗包含用例名、来源、日期、错误类型、执行状态等筛选项，支持选择失败用例，展示用例名、用例描述、错误类型、断言、执行状态、错误信息/确认信息；顶部有 Jenkins 任务、测试账号、替换测试账号、更多菜单；更多菜单含失败重试和一键失败重试。
- Stage 9 浏览器检查：`/platform` 注入本地登录态和 mock 测试任务数据后可展示模块通过率；点击失败重试可打开失败用例弹窗；桌面和移动端无明显文本重叠，控制台无 warning/error。
