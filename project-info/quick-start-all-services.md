# 当前项目所有服务快速启动说明

## 目标与边界

本文档用于在本机准备 AiApiTest-DWP 的 MySQL、Jenkins、DRF backend、Vue frontend 和 Jenkins 同步 worker，并通过固定 Jenkins 环境 Job 完成冒烟或全量验收。

- MySQL 与 Jenkins 只由主人/平台运维 bootstrap。
- backend、frontend、`jenkins-sync-worker` 的依赖、镜像、schema、部署、健康检查和测试只由 `AiApiTest-DWP-Platform-Bootstrap` 管理。
- AI 只能使用固定 Job helper，不能直接启动 Compose 应用服务、Django `runserver`、Vite、worker，也不能在宿主机或容器内安装依赖。
- `.env`、运行日志、报告和真实凭据不提交 Git。

## 1. 准备本地 `.env`

在仓库根目录首次复制公共模板：

```powershell
Copy-Item .env.example .env
```

Linux、macOS 或 Git Bash：

```bash
cp .env.example .env
```

复制后先停止启动流程，人工补齐私有区，再运行基础服务脚本。模板不是可直接启动的完整配置。

### 公共配置

`.env.example` 只保留 12 项部署差异：

| 类别 | 配置项 |
| --- | --- |
| 平台网络 | `PLATFORM_BIND_HOST`、`PLATFORM_PUBLIC_HOST`、`PLATFORM_PUBLIC_SCHEME` |
| 宿主机端口 | `MYSQL_HOST_PORT`、`JENKINS_HTTP_PORT`、`JENKINS_AGENT_PORT`、`BACKEND_HOST_PORT`、`FRONTEND_HOST_PORT` |
| 必要运维选项 | `PROJECT_WORKSPACE`、`DOCKER_GID`、`CI_RUN_RETENTION_DAYS`、`FRONTEND_PLAYWRIGHT_BASE_IMAGE` |

本地 `.env` 的公共区必须与模板保持相同键名、顺序、分组和注释，值可以按部署环境修改。所有服务公开 URL 由统一协议、公开主机和对应端口派生，不再逐项配置 URL。

### 私有配置

下列 16 项只存在于本地 `.env`，不得添加到 `.env.example`：

| 类别 | 配置项 |
| --- | --- |
| 数据库 | `MYSQL_ROOT_PASSWORD`、`DB_USER`、`DB_PASSWORD` |
| 应用密钥 | `DJANGO_SECRET_KEY`、`AUTH_TOKEN_SECRET` |
| Jenkins API | `JENKINS_USERNAME`、`JENKINS_API_TOKEN` |
| 初始化管理员 | `INITIAL_ADMIN_USERNAME`、`INITIAL_ADMIN_DISPLAY_NAME`、`INITIAL_ADMIN_PASSWORD` |
| 环境目录 SCM | `JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL`、`JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH`、`JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID`、`JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID` |
| 环境目录服务认证 | `JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID`、`ENVIRONMENT_CATALOG_SERVICE_TOKEN` |

`MYSQL_ROOT_PASSWORD` 只用于 MySQL 管理、初始化和健康检查；backend、worker 与一次性 bootstrap 只使用 `DB_USER`、`DB_PASSWORD`。启用环境目录同步时，`JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID` 指向的 Jenkins Secret Text 内容必须与注入 backend 的 `ENVIRONMENT_CATALOG_SERVICE_TOKEN` 相同；Preflight 只报告缺失键或状态，不输出值。

以下内容已经代码化，不能通过 `.env` 修改：Job 名、Jenkins 40 executors、内部 service name/端口、容器内 workspace、API 路径 `/api/v1`、请求和轮询超时、数据库名、时区及 Cookie 固定策略。旧 Daily Job 删除开关已退役，遗留 Job 由主人/平台运维人工迁移。

## 2. 启动 MySQL 与 Jenkins

以下入口仅供主人/平台运维使用。

Windows PowerShell：

```powershell
.\scripts\deploy-docker.ps1
```

Linux、macOS 或 Git Bash：

```bash
bash scripts/deploy-docker.sh
```

脚本只管理 `mysql` 与 `jenkins`，不会启动三项应用服务。它会等待本地 Jenkins Init Groovy 生成运行时 API 凭据，并在不打印令牌的前提下更新私有 `.env`。若脚本因 `.env` 缺失而复制模板，应先补齐私有区，再重新运行。

Jenkins 启动时会幂等创建或修复代码固定的 `AiApiTest-DWP-Platform-Bootstrap`。不要在 Jenkins 页面手工创建同名或旁路环境 Job。

## 3. 构建应用环境

可以在 Jenkins 页面构建 `AiApiTest-DWP-Platform-Bootstrap`，也可以使用唯一 helper 触发同一 Job。

Windows PowerShell：

```powershell
# 默认：全量构建应用镜像并执行冒烟
.\scripts\trigger-platform-bootstrap.ps1

# 增量检查并执行全量回归
.\scripts\trigger-platform-bootstrap.ps1 -BuildAll false -RunFullTests true
```

Linux、macOS 或 Git Bash：

```bash
# 默认：全量构建应用镜像并执行冒烟
bash scripts/trigger-platform-bootstrap.sh

# 增量检查并执行全量回归
bash scripts/trigger-platform-bootstrap.sh --build-all false --run-full-tests true
```

固定 Job 依次执行八个阶段：`Checkout/Workspace`、`Bootstrap Preflight`、`Dependency Assurance`、`Schema & Initial Data`、`Deploy`、`Health`、`Tests`、`Archive & Summary`。仅 `Schema & Initial Data` 可通过一次性 `backend-bootstrap` 服务执行 migration、环境种子和 bootstrap 管理员初始化。

## 4. 访问与验收

平台公开入口按以下规则派生：

| 入口 | 地址规则 |
| --- | --- |
| Jenkins | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${JENKINS_HTTP_PORT}` |
| 前端 | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${FRONTEND_HOST_PORT}/platform` |
| 后端接口文档 | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${BACKEND_HOST_PORT}/api/docs/` |
| 后端业务 API | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${BACKEND_HOST_PORT}/api/v1` |

登录使用本地 `.env` 的初始化管理员账号。通过标准包括：

- MySQL 为 `healthy`，Jenkins 可访问。
- 固定环境 Job 八阶段成功。
- backend、frontend、worker 健康检查通过。
- Jenkins Build Summary、artifact 和可用 Allure 结果已归档。
- 前端能登录并访问已授权平台页面。

Playwright 的本地 Vite webServer 固定使用 HTTP 和 4173 端口，并从 `PLATFORM_BIND_HOST` 派生可连接回环地址；外部公开主机或 `PLATFORM_PUBLIC_SCHEME=https` 不会错误地套用到本地明文测试服务。

## 5. 故障排查

| 现象 | 处理方式 |
| --- | --- |
| `CONFIG_ENV_CONTRACT_DRIFT` | 按错误中的键名、行号和类型修正 `.env` 公共区/私有区；不要把值贴入日志或文档。 |
| MySQL 未运行或不健康 | 由主人/平台运维修复基础服务和已有数据卷凭据，再重新构建固定 Job。 |
| Jenkins 认证失败 | 核对私有 `JENKINS_USERNAME`、`JENKINS_API_TOKEN`，必要时由主人/平台运维重新执行基础服务 bootstrap。 |
| 环境目录同步预检失败 | 核对 SCM 四项配置、Jenkins service credential ID 与 backend 服务令牌闭环，不输出令牌。 |
| Job 不存在或代码未更新 | 核对 `PROJECT_WORKSPACE` 是否指向当前仓库，并由主人/平台运维修复 Jenkins bootstrap/Init Groovy。 |
| 应用依赖、Deploy、Health 或 Tests 失败 | 阅读同一次 Jenkins 构建的结构化诊断和 artifact，修复根因后重建同一 Job；禁止旁路启动应用。 |

已有 MySQL 数据卷初始化后，修改 `.env` 不会自动更新 root 或应用用户密码。凭据变更必须由主人/平台运维按数据策略同步处理；禁止用 `down -v`、删除 volume、清库或自动 rollback 作为普通修复手段。

更完整的服务边界、参数和安全说明见 `docker/DEPLOYMENT.md` 与 `jenkins/README.md`。
