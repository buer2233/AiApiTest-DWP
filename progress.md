# 开发流程与架构重构进度

## 2026-06-28 第一个需求：用户登录注册和测试用例展示

- 已读取并使用 `using-superpowers`、`planning-with-files`、`brainstorming`、`product-requirements`，确认本需求进入需求分析与澄清门禁阶段。
- 已读取 TDD、Django TDD、API 设计、Vue 最佳实践、Vue 测试和前端设计技能，作为后续开发约束；需求冻结前不进入业务编码。
- 已读取根计划、发现记录、进度记录、README、需求模板、架构说明、后端规则和前端规则。
- 已检查当前 Git 状态：`progress.md` 已修改；`back-end/.coverage`、`front-end/.vite/`、`front-end/playwright-report/`、`front-end/test-results/`、`front-end/tests/` 为未跟踪或运行产物；`back-end/apps/` 等目录显示 ignored/缓存状态。
- 已递归检查 `back-end/apps`、`back-end/config`、`back-end/common`、`back-end/tests`，确认只有 `__pycache__` 与 `.pyc` 缓存，没有可维护 `.py` 源码。
- 已检查 `front-end/`，确认只有规则文件、构建/依赖运行产物和三张测试截图，缺少可维护的 Vue 工程源文件。
- 已将 `task_plan.md` 顶部切换为当前活动计划，保留旧架构计划作为历史上下文。
- 已新增正式需求说明书草案：`project-info/demand/用户登录注册和测试用例展示-需求说明.md`，当前状态为“澄清中”，等待主人裁决 §0 的 6 个待澄清项后才能冻结。
- 已回写主人对 Q1-Q6 的裁决：active 用户、DRF Token、扫描同步入库、邀请码注册、完整用例字段、admin 同步权限。
- 因邀请码注册引入新的关键设计点，已在需求 §0 新增 Q7：邀请码来源与管理方式，推荐使用环境变量配置单个共享邀请码。
- 已回写主人对 Q7 的裁决：新增邀请码表和后台管理能力；需求说明书已补充 F3 邀请码管理、`registration_invite_code` 表、邀请码管理 API、邀请码管理页面和对应验收标准。
- 当前需求 §0 已全部闭环，等待主人在 §14 明确冻结后进入功能测试用例和 UI 原型阶段。
- 主人已回复“冻结 然后进行之后的步骤”；已将需求说明书状态改为“已冻结”，冻结人为“主人”，冻结日期为 2026-06-28。
- 已完成后端 RED 验证：在 `back-end/` 执行 `python -m pytest tests --maxfail=1 -q`，失败原因为 `ImportError: No module named 'config.settings.test'`，且 pytest-django 提示找不到 Django project / `manage.py`，符合源码尚未实现的预期失败。
- 已按后端 TDD GREEN 阶段新增可维护 DRF 工程源码：`manage.py`、`config/settings/*`、`config/urls.py`、`common/*`、`apps/accounts/*`、`apps/testcases/*`、迁移文件和 `requirements.txt`。
- 后端首轮 GREEN 执行 `python -m pytest tests -q` 时 17 passed / 1 failed；失败点为重复邀请码返回 400，契约要求 409。已使用 `systematic-debugging` 定位为 DRF 自动唯一校验覆盖业务错误码，并修复。
- 已完成后端 GREEN 验证：在 `back-end/` 执行 `python -m pytest tests --cov=apps --cov=common --cov-report=term-missing`，结果为 `18 passed in 1.17s`，总覆盖率 `94%`，无 warning。
- 已按独立前端审查补充 RED 测试并修复：member 直达 `/invite-codes` 被拦截、admin 可二次确认禁用邀请码、测试用例/邀请码分页、测试用例类名列、注册字段级错误、401 凭据失效清理登录态；核心 E2E `auth-and-testcases.spec.ts` 已验证 `8 passed`。
- 已按独立后端审查补充 RED 测试并修复：并发唯一冲突转 `409 duplicate_user`、过期邀请码状态持久化、无效 Token 统一 `unauthorized`、邀请码数据库约束、非法 `sync_status`、同步源缺失 `500 sync_source_missing`、Allure 标题解析；后端相关测试已验证 `25 passed`，覆盖率 `95%`。
- 后端复审无阻塞问题；已按复审建议补充 `max_uses >= 1` 数据库约束直接测试和 `@allure.story` 无 docstring 解析测试。
- 前端复审无阻塞问题；已按复审建议补充邀请码创建字段级错误 Playwright 测试并实现对应字段错误展示。
- 已完成最终后端验证：`python -m pytest tests --cov=apps --cov=common --cov-report=term-missing`，结果 `26 passed in 1.44s`，总覆盖率 `95%`。
- 已完成最终前端验证：`npm audit --json` 为 0 vulnerabilities；`npm run build` 通过；`npx playwright test --project=chromium` 结果 `10 passed`，并刷新 4 张关键页面截图。
- 前端构建仍有非阻塞警告：`@vueuse/core` 的 pure 注释被 Rolldown 忽略，主 chunk 超过 500k；已记录到验收包剩余风险。

## 2026-06-26

- 已读取项目根目录和用户提供的全局规则。
- 已按要求读取必须技能 `using-superpowers` 与 `planning-with-files`。
- 已使用 `brainstorming`，并遵守先设计确认后实施的硬门禁。
- 已读取 `product-requirements`，用于后续需求质量评估和目标澄清。
- 已确认用户愿意启用浏览器可视化辅助。
- 已读取 `brainstorming/visual-companion.md`。
- 已读取根目录 `AGENTS.md`、`README.md` 和各核心模块 `AGENTS.md`。
- 已将 `task_plan.md`、`findings.md`、`progress.md` 从旧的前端清理任务切换为当前架构重构任务。
- 已启动浏览器可视化辅助服务：`http://localhost:63610`。
- 已推送第一张讨论草图：当前事实、待确认方向和三种执行主干选项。
- 用户反馈倾向方案 B：统一通过 Jenkins 执行企业流水线，认为更规范且扩展性更高。
- 用户进一步确认采用严格 Jenkins 执行主干：平台所有测试执行都必须通过 Jenkins。
- 已分析用户提供的三张目标页面截图和字段示例。
- 已读取当前 `api-test/tools/ci_runner.py` 和 `jenkins/scripts/api-test-pipeline.groovy`，确认现有执行器支持基础重试模式，但当前 summary 不足以直接支撑模块统计和失败用例明细入库。
- 已读取 `api-design` 技能，用于后续 DRF API 资源和响应格式设计。
- 已记录三张核心业务表：模块展示快照、失败用例记录、Jenkins 执行记录。
- 用户提醒当前应回到架构设计阶段，详细需求先作为草稿沉淀。
- 已新增需求草稿：`project-info/demand/需求草稿-测试平台架构阶段.md`。
- 已停止依赖不可访问的浏览器可视化辅助，后续先使用文字方案推进架构讨论。
- 用户确认不拆分多个仓库，继续使用单仓库结构。
- 已将建议表设计草案补充到需求草稿文档。
- 已进行前端技术栈架构评估，推荐 Vue 3 + Vite + TypeScript + Element Plus 作为前端主栈。
- 已按新流程和架构重写根目录 `AGENTS.md`。
- 已简化更新根目录 `README.md`。
- 已将 `project-info/project_detail/项目架构说明书.md` 重命名并重写为 `project-info/project_detail/project-architecture.md`。
- 已使用 drawio-skill 生成新架构图源文件 `project-info/project_detail/project-architecture.drawio`。
- 已运行 draw.io XML 校验：0 error(s), 0 warning(s)。
- 本机已安装 draw.io desktop CLI：`C:\Users\admin\AppData\Local\Programs\draw.io\draw.io.exe`，版本 30.2.4。
- 已导出普通预览 PNG：`project-info/project_detail/project-architecture.png`。
- 已导出带嵌入 XML 的可编辑 PNG：`project-info/project_detail/project-architecture.drawio.png`，并已执行 PNG 修复脚本。
- 已依据当前架构和固定 loop 更新所有既有子目录 `AGENTS.md`：`api-test/`、`back-end/`、`front-end/`、`jenkins/`、`project-info/`、`project-info/demand/`、`project-info/test_case/`、`project-info/UI/`、`project-info/project_detail/`。
- 已新增 `docker/AGENTS.md`，补齐基础设施目录的容器设计、验证和安全规则。

## 2026-06-27

- 开始执行整体 Docker 化架构增强任务。
- 已确认本轮需要更新 `docker/AGENTS.md`、新增 `docker/CLAUDE.md`、更新根目录 `AGENTS.md`、`project-info/project_detail/AGENTS.md`、`project-info/project_detail/project-architecture.md`，并重绘架构图。
- 已读取 drawio-skill 和 architecture diagram preset，后续按 draw.io XML 校验和 PNG 导出流程处理。
- 更新 draw.io XML 的临时 Python 生成尝试失败，未写出文件；已切换为 `apply_patch` 直接维护源文件。
- 已更新 `docker/AGENTS.md`，加入后期完整 Docker Compose 打包部署预案、服务边界、落地顺序、验证要求和安全要求。
- 已新增 `docker/CLAUDE.md`，内容为 `@AGENTS.md`。
- 已更新根目录 `AGENTS.md` 和 `project-info/project_detail/AGENTS.md`，明确后续设计和开发必须满足整体 Docker 化部署能力。
- 已更新 `project-info/project_detail/project-architecture.md`，新增整体 Docker 化部署架构章节，并补充容器化链路、服务边界、报告产物和安全约束。
- 已重绘 `project-info/project_detail/project-architecture.drawio`，并导出 `project-architecture.png` 与 `project-architecture.drawio.png`。
- 已运行 draw.io XML 校验：0 error(s), 0 warning(s)。
- 已运行 `git diff --check`：无空白错误，仅出现 Windows 换行转换提示。
- 开始补充开发流程检查点和 subagent 并行协作规则。
- 已读取 `subagent-driven-development`，确认 subagent 更适合有明确输入和边界的独立任务，且需要主 agent 做汇合和质量门禁。
- 已在根目录 `AGENTS.md` 增加流程检查点和并行规则，并补充 `subagent-driven-development` 为全局推荐技能。
- 已在需求、测试用例、UI、后端、前端阶段 AGENTS 中补充架构影响评估、API 契约冻结、容器化兼容检查和 UI 覆盖校准要求。
- 已更新 `project-info/project_detail/project-architecture.md` 的开发流程架构，明确需求后可并行测试设计和 UI 第一版，后续通过汇合门禁再进入后端和前端开发。
- 开始按最新架构方案重绘项目架构图，并新增完整开发过程流程图。
- 本轮图形产物限定在 `project-info/project_detail/`，包括 `project-architecture.*` 和 `execution-flow.*`。
- 已重绘 `project-info/project_detail/project-architecture.drawio`，并重新导出普通 PNG 与可编辑 PNG。
- 已新增 `project-info/project_detail/execution-flow.drawio`，并导出 `execution-flow.png` 与 `execution-flow.drawio.png`。
- 已校验 `project-architecture.drawio` 和 `execution-flow.drawio`：均为 0 error(s), 0 warning(s)。
- 已检查四个 PNG 文件头尾，均为有效 PNG；已通过图片预览确认架构图和流程图可读。
# 2026-06-28 服务启动验收任务

- 收到主人要求：开启项目所有服务，并将服务和账号信息写入 `server_acount.md`，用于项目验收测试。
- 已确认本任务属于运维/联调启动，不涉及业务行为变更；不进入需求 loop 编码阶段，但仍需遵守安全规范，不写入真实生产凭据。
- 已读取根目录 Compose、`.env`、后端/前端模块说明和启动脚本信息；当前基础 Compose 包含 MySQL 与 Jenkins，后端和前端需要分别以本地开发服务启动。
- 启动基础服务时发现已有旧容器名冲突；确认 `aiapitest-mysql`、`aiapitest-jenkins` 为停止状态旧容器后，已复用启动，保留既有 volume。
- MySQL 旧容器创建时使用 `MYSQL_ALLOW_EMPTY_PASSWORD=yes`，当前 `.env` 中 root 密码不适用于旧数据卷；已在容器内创建本地验收数据库账号 `hermes`。
- 旧库 `ai_api_test_platform` 存在迁移记录与实际表结构不一致问题（如 `auth_permission` 缺失、`accounts_user.status` 缺失），为避免破坏旧库，改用新建本地验收库启动后端。
- 已创建验收库 `ai_api_test_platform_acceptance`，完成 Django 全量迁移，创建本地验收管理员账号，账号明细仅写入被 `.gitignore` 忽略的 `server_acount.md`，同步测试用例 26 条。
- 已启动本地后端 `http://127.0.0.1:8000/` 与前端 `http://127.0.0.1:5173/`；已验证登录接口、用例列表接口、前端登录页、Jenkins 登录页均可访问。
- 已通过 Playwright 浏览器级验证：使用本地验收管理员账号登录前端后跳转到 `/test-cases`，页面显示 26 条用例；唯一控制台错误为 `favicon.ico` 404，不影响本次验收。
- 已将服务入口和本地验收账号写入 `server_acount.md`；该文件被 `.gitignore` 忽略，符合账号信息不入库的安全规则。
