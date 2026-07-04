# 初始版本收尾-Stage2-MySQL与环境变量配置收尾-功能测试用例

## 概览

| 项 | 内容 |
| --- | --- |
| 需求来源 | `project-info/demand/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-需求说明.md` |
| 需求分级 | M |
| UI 原型 | 本需求不新增业务页面，UI 原型阶段按需求说明裁剪 |
| 覆盖范围 | MySQL 正式库、根 `.env` 配置、前端/Playwright 环境变量、Jenkins 变量化、文档和脱敏模板 |
| 更新时间 | 2026-07-04 |

## 1. 功能测试

### TC-F-001 后端正式配置默认使用 MySQL

- **关联 AC**：AC1.1
- **优先级**：P0
- **前置条件**：根 `.env` 已配置 `MYSQL_DATABASE`、`MYSQL_ROOT_PASSWORD`、`MYSQL_BIND_HOST`、`MYSQL_HOST_PORT`。
- **操作步骤**：
  1. 执行 `cd back-end && pytest tests/test_environment_settings.py -q`。
  2. 检查 `build_database_config()` 输出。
- **预期结果**：
  - `DATABASES["default"]["ENGINE"]` 为 `django.db.backends.mysql`。
  - 数据库名、主机、端口和密码来源与 `MYSQL_*` / `DB_*` 环境变量一致。
- **后置条件**：不修改真实 `.env`。

### TC-F-002 Docker MySQL 可连接且迁移完成

- **关联 AC**：AC1.2
- **优先级**：P0
- **前置条件**：Docker Desktop 已启动，`aiapitest-mysql` 容器运行中。
- **操作步骤**：
  1. 执行 `docker ps --filter name=aiapitest-mysql`。
  2. 执行 `cd back-end && python manage.py migrate --check`。
- **预期结果**：
  - MySQL 容器状态为 `Up`。
  - `migrate --check` 返回 0，输出 `migrate_check=ok`。

### TC-F-003 SQLite 验收数据已迁移且 SQLite 文件保留

- **关联 AC**：AC1.2
- **优先级**：P0
- **前置条件**：已从 `back-end/db.sqlite3` 导出并导入用户、邀请码数据。
- **操作步骤**：
  1. 执行 Django shell 查询 `connection.vendor`、`UserAccount.objects.count()`、`InvitationCode.objects.count()`。
  2. 检查 `back-end/db.sqlite3` 文件是否仍存在。
- **预期结果**：
  - `database_vendor=mysql`。
  - `user_account=2`，`invitation_code=2`。
  - `back-end/db.sqlite3` 未删除，继续作为本轮验收备份。

### TC-F-004 初始化管理员命令幂等

- **关联 AC**：AC1.3
- **优先级**：P1
- **前置条件**：`.env` 已配置初始化管理员变量。
- **操作步骤**：
  1. 执行 `cd back-end && python manage.py init_admin`。
  2. 观察命令输出。
- **预期结果**：
  - 已存在管理员时输出幂等提示。
  - 输出不包含真实密码或 token。

### TC-F-005 pytest 测试环境仍使用 SQLite

- **关联 AC**：AC1.4
- **优先级**：P0
- **前置条件**：后端测试 settings 可用。
- **操作步骤**：
  1. 执行 `cd back-end && pytest --disable-warnings`。
  2. 检查测试结果和覆盖率。
- **预期结果**：
  - 全部后端测试通过。
  - 测试环境不依赖 Docker MySQL，覆盖率输出可用于验收。

### TC-F-006 Vite dev server 和代理读取根 `.env`

- **关联 AC**：AC2.1、AC2.2、AC2.4
- **优先级**：P0
- **前置条件**：`front-end/vite.config.ts` 使用 `envDir` 指向仓库根目录。
- **操作步骤**：
  1. 执行 `cd front-end && npm run test:unit`。
  2. 检查 `resolveFrontendEnv()` 单测。
- **预期结果**：
  - dev host/port 使用 env 值。
  - `/api` 代理目标使用 env 值。
  - `VITE_API_BASE_URL` 未配置时默认 `/api/v1`。
  - `VITE_API_TIMEOUT_MS` 能驱动 Axios 请求超时时间。

### TC-F-007 Playwright 运行地址和权限 origin 保持一致

- **关联 AC**：AC2.3
- **优先级**：P0
- **前置条件**：`front-end/playwright.config.ts` 从根 `.env` 加载配置。
- **操作步骤**：
  1. 执行 `cd front-end && npm run test:unit`。
  2. 执行 `cd front-end && npm run test:e2e`。
- **预期结果**：
  - `baseURL`、`webServerUrl`、`permissionOrigin` 来自同一派生值。
  - Playwright 18 条 E2E 用例全部通过。

### TC-F-008 `.env.example` 覆盖脱敏启动变量

- **关联 AC**：AC3.1、AC3.2
- **优先级**：P0
- **前置条件**：`.env.example` 已更新。
- **操作步骤**：
  1. 执行 `pytest jenkins\tests\test_docker_deployment_static.py -q`。
  2. 检查变量和敏感值断言。
- **预期结果**：
  - MySQL、Django、Auth、前端、Playwright、Jenkins、初始化管理员变量齐全。
  - 不包含真实密码、token、cookie 或生产地址。

### TC-F-009 Jenkins Pipeline 默认路径从环境变量读取

- **关联 AC**：AC3.1、AC3.2
- **优先级**：P1
- **前置条件**：`jenkins/scripts/api-test-pipeline.groovy` 已变量化。
- **操作步骤**：
  1. 执行 `pytest jenkins\tests\test_pipeline_static.py -q`。
  2. 检查 `JENKINS_DEFAULT_CASE_PATH`、`JENKINS_API_TEST_DIR`、`JENKINS_PYTHON_VENV_DIR` 断言。
- **预期结果**：
  - Jenkins 保留执行编排职责。
  - 默认 case path、api-test 目录和虚拟环境目录可由环境变量覆盖。
  - Docker Jenkins 容器显式注入这些变量，避免只停留在 `.env.example` 文档层。

### TC-F-010 流程文档纳入 `.env` 标准

- **关联 AC**：AC3.3、AC3.4
- **优先级**：P1
- **前置条件**：根 `AGENTS.md`、`project-info/AGENTS.md`、快速启动和 Docker 部署文档已更新。
- **操作步骤**：
  1. 检查文档是否说明真实 `.env` 不提交、`.env.example` 脱敏提交。
  2. 检查启动命令是否优先使用根 `.env`。
- **预期结果**：
  - 后续需求必须把可变配置集中到根 `.env` / `.env.example`。
  - 文档不要求写死本机绝对路径或手工设置一批 `$env:MYSQL_*`。

## 2. 边界和异常测试

### TC-E-001 非法端口回退安全默认值

- **关联 AC**：AC2.1、AC2.3
- **优先级**：P1
- **操作步骤**：执行 `cd front-end && npm run test:unit`。
- **预期结果**：`parsePort("not-a-port", 5173)` 和空值均回退到默认端口。

### TC-ERR-001 unit 测试不误收集 Playwright E2E

- **关联 AC**：AC2.3
- **优先级**：P1
- **操作步骤**：执行 `cd front-end && npm run test:unit`。
- **预期结果**：Vitest 只收集 `tests/**/*.test.ts` 和 `src/**/*.{test,spec}.ts`，不执行 `e2e/**`。

### TC-ERR-002 旧 MySQL volume 与 `.env` 改密风险被文档化

- **关联 AC**：AC1.2、AC3.1
- **优先级**：P2
- **操作步骤**：检查 `docker/DEPLOYMENT.md` 与 `project-info/quick-start-all-services.md`。
- **预期结果**：文档明确 MySQL root 密码、库名、宿主机端口和持久化 volume 属于启动后不建议修改项。

## 覆盖矩阵

| AC 编号 | 覆盖用例 | 覆盖状态 |
| --- | --- | --- |
| AC1.1 | TC-F-001 | 完整 |
| AC1.2 | TC-F-002、TC-F-003、TC-ERR-002 | 完整 |
| AC1.3 | TC-F-004 | 完整 |
| AC1.4 | TC-F-005 | 完整 |
| AC2.1 | TC-F-006、TC-E-001 | 完整 |
| AC2.2 | TC-F-006 | 完整 |
| AC2.3 | TC-F-007、TC-E-001、TC-ERR-001 | 完整 |
| AC2.4 | TC-F-006 | 完整 |
| AC3.1 | TC-F-008、TC-F-009、TC-ERR-002 | 完整 |
| AC3.2 | TC-F-008、TC-F-009 | 完整 |
| AC3.3 | TC-F-010 | 完整 |
| AC3.4 | TC-F-010、TC-ERR-002 | 完整 |
