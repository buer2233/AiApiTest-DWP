# back-end/AGENTS.md

本目录是 Django REST Framework 后端。进入 `back-end/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `back-end/` 是平台编排和数据中心，负责用户、权限、任务、模块快照、失败用例、Jenkins 触发/同步、报告入口和审计。
- 后端只通过 Jenkins API 触发或同步执行，不直接执行 pytest，不重复实现 `api-test/tools/ci_runner.py` 的参数拼接、失败重试或 Allure 生成规则。
- 后端数据以 MySQL 为主，面向前端提供稳定 DRF API。

## 固定 loop 中的位置

- 后端开发属于固定 loop 第 4 阶段。
- 开发前必须存在同一需求命名的需求说明书和功能测试用例；涉及页面操作时还应参考 UI 原型。
- 开发前必须确认 API 契约已经冻结，至少包含路径、方法、请求参数、响应字段、错误码、分页筛选、权限和关键状态流转。
- 后端必须包含 Swagger/OpenAPI 接口文档；新增或变更 DRF 接口时，必须同步维护 schema 注解、请求/响应字段、错误码、权限说明和筛选分页参数，并补充 Swagger 文档端点回归测试。
- 开发前必须确认架构影响评估已完成；如果影响 Jenkins、`api-test`、Docker、报告协议或权限模型，应同步对应模块说明后再编码。
- 开发顺序必须是：先写并运行 pytest/pytest-django 接口测试，确认失败由目标行为缺失导致，再做最小 DRF 实现、目标测试 GREEN、重构和相关回归，遵循 `RED -> GREEN -> REFACTOR`。
- 如果需求文档、测试用例或表设计缺失，应先回到 `project-info/` 对应阶段补齐，不直接进入编码。
- 阶段完成必须留存 pytest 运行输出与覆盖率证据，并补全 `需求名-可追溯矩阵.md` 的后端实现列。
- 接口实现完成后必须按根规则经过独立 review subagent 对抗审查：实现者不得自审，问题修复并由同一 reviewer 复审、阻断问题清零后再进入下一阶段。自主流水线整体执行方式见 `docs/自主开发流水线.md`。

## 后端工程方法与 Skill 选择

- API 设计必须检查资源语义、路径与 HTTP 方法、请求校验、HTTP 状态、统一错误模型、鉴权与权限、分页筛选排序、幂等、并发冲突、兼容性和关键状态流转。
- 新增或变更接口必须同步 serializer、权限类、查询行为、OpenAPI schema、消费者说明和契约测试，禁止只改 view 形成隐式协议。
- Python 代码保持职责单一、显式依赖、清晰类型和可测试边界；外部 Jenkins/HTTP/时间源在测试中使用可控 fake 或 mock，不把真实网络当作单元测试前置条件。
- 当前会话可用且任务匹配时，可使用 `python-testing` 辅助 pytest fixture、参数化、mock 和覆盖率设计；Skill 不可用不影响本文件 TDD 与覆盖要求。
- 接口失败按根目录的根因排查协议处理，先区分规格、权限、序列化、数据库、外部服务和测试环境问题，再做最小修复。

## 模块职责

- 用户登录、登出、当前用户信息和角色权限入口。
- 模块展示主表数据，包括通过率、通过数、失败数、错误数、执行时间和报告入口。
- 失败用例记录表，采用追加写入；状态至少包含 `失败`、`通过`、`跳过`、`不展示`。
- Jenkins 执行记录表，采用追加写入；记录 job、build、任务名、状态、环境和报告归档信息。
- Jenkins job/build 查询、触发、console log 查询和执行产物同步 API。
- Allure 报告入口、执行审计和关键状态变更记录。

## 数据和状态规则

- 主表用于展示每个模块的最新快照，同一环境和模块执行后更新对应记录。
- 失败表不删除历史数据；模块重试前需要将当前模块旧失败用例标记为 `不展示`，新失败用例先标记为 `失败`。
- 失败重试通过后，将对应失败用例状态更新为 `通过`。
- 用户只能在 `失败` 和 `跳过` 两个状态之间手动切换。
- 失败用例界面展示 `失败` 和 `跳过`；通过率计算只把 `失败` 状态纳入扣减，`跳过` 不降低通过率。
- Jenkins 表不删除历史数据，每次触发和同步都新增执行记录。

## 技术约定

- 使用 Django + Django REST Framework + MySQL。
- 配置从环境变量或本地私有配置读取，不提交真实凭据。
- 浏览器可见的外部服务地址必须由根公共配置中的平台公开主机、协议和服务宿主机端口派生；容器内部依赖使用代码化的 Compose 服务名与固定容器端口。不得为同一服务增设独立 URL 环境变量，也不得写死个人机器地址或路径。
- 权限第一版可让 `admin` 和 `member` 权限一致，但代码结构要保留管理员专属权限入口。
- Jenkins client 测试必须使用 fake HTTP 响应，不依赖真实 Jenkins 服务。
- API 响应字段应保持平台通用，不写入不可迁移的业务常量。
- Swagger/OpenAPI 文档通过项目内依赖和相对路由提供，不写死本机地址、宿主机端口、个人目录、真实凭据或生产 URL。

## 禁止事项

- 不提交真实账号、密码、token、cookie、Jenkins API Token、租户密钥、生产 URL 或敏感地址。
- 不在后端直接 shell 调用 pytest 或 Allure。
- 不删除失败用例历史和 Jenkins 执行历史，除非后续需求明确设计归档或清理策略。

## 平台环境唯一入口（强制）

- 平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，AI 必须且只能触发固定 Jenkins 环境 Job。
- 固定环境 Job 由本地 Compose Jenkins 启动时通过版本化 init Groovy 幂等创建或修复；主人启动 MySQL/Jenkins bootstrap 后只需在 Jenkins 页面点击构建，不得手工创建另一条旁路 Job。
- Windows 唯一入口为 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash 唯一入口为 `scripts/trigger-platform-bootstrap.sh`。用户在 Jenkins 页面手工点击同一 Job 也使用相同 Pipeline、参数、阶段和结果契约。
- AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install/npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 替代环境 Job。
- MySQL 与 Jenkins 仅由主人/平台运维按 `docker/DEPLOYMENT.md` 完成 bootstrap；环境 Job/helper 永不管理这两个基础服务。AI 只能检查并反馈，不能代替主人/平台运维启动。
- 固定 Job 的 `Schema & Initial Data` 阶段可通过一次性 `backend-bootstrap` 服务执行 `migrate --noinput`、`seed_environment --reconcile`、`sync_modules --reconcile`、`init_admin --bootstrap-only`；AI、宿主机、常驻 backend/worker、readiness 和其他 Job 仍禁止执行 migration 或初始化管理员。禁止 `down -v`、volume 删除、`chmod 666 /var/run/docker.sock`、`collectstatic`、自动 rollback 或输出真实凭据。环境失败必须阅读 Jenkins 结构化诊断，引导主人修复后重新构建，不能旁路处理。
