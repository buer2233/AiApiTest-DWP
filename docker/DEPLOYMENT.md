# Docker Deployment

![AiApiTest-DWP Docker 服务边界与启动路径](../docs/images/platform-bootstrap/docker-service-lifecycle-flow-4k.png)

本文档说明当前 AiApiTest-DWP 的 Docker 构建方式、服务边界和供主人/平台运维使用的启动流程。它回答一个容易混淆的问题：Compose 确实声明了多个服务，但**不能以直接拉起全部 Compose 服务替代平台环境构建**。完整可用状态必须由固定 Jenkins 环境 Job 验证。

> **仅主人/平台运维执行，AI 不得执行。** 本文中的 Docker bootstrap 命令只用于基础服务；环境 Job/helper 永不管理 MySQL 与 Jenkins。

## 先看结论

平台分为两个生命周期边界：

| 边界 | 服务 | 谁启动和维护 | 目的 |
| --- | --- | --- | --- |
| 基础服务 | `mysql`、`jenkins` | 主人或平台运维 | 为平台提供数据库与构建控制器；数据卷独立持久化。 |
| 应用服务 | `backend`、`frontend`、`jenkins-sync-worker` | `AiApiTest-DWP-Platform-Bootstrap` | 统一执行依赖检查、镜像构建、部署、健康检查和测试。 |
| 按需工具镜像 | `api-runner` | Jenkins 测试流水线 | 仅 `tools` profile 使用，不是第六个常驻服务。 |

因此，正确的首次使用路径是：

1. 主人或平台运维启动 `mysql` 与 `jenkins`。
2. Jenkins 启动时运行版本化 Init Groovy，幂等创建或修复 `AiApiTest-DWP-Platform-Bootstrap`。
3. 在 Jenkins 页面构建该 Job，或使用仓库 helper 触发同一 Job。
4. Job 成功完成后，才通过 `.env` 配置的前端、后端公开地址使用平台。

直接运行 `docker compose up -d` 可能让多个容器显示为运行中，但会绕过依赖完整性、镜像输入哈希、健康检查、冒烟或全量测试以及 Jenkins 证据归档，不能作为当前平台“已可用”的判断依据。

## 构建与服务实现

`docker-compose.yml` 的 Compose project 为 `aiapitest-dwp`，所有服务使用 `aiapitest-platform` 网络。默认 Compose 服务如下；默认 Jenkins controller 构建 `docker/jenkins/Dockerfile` 工具链镜像 `aiapitest-jenkins:lts-jdk17-tools`，不是可选 override。

| 服务或镜像 | 实现方式 | 关键连接 | 对外入口 |
| --- | --- | --- | --- |
| `mysql` | MySQL 8.4，持久化卷 `aiapitest-mysql-data` | Compose 内为 `mysql:3306` | `${PLATFORM_BIND_HOST}:${MYSQL_HOST_PORT}`。 |
| `jenkins` | 由 `docker/jenkins/Dockerfile` 构建工具链镜像 | 挂载 Docker Socket、项目源码和 Init Groovy | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${JENKINS_HTTP_PORT}`。 |
| `backend` | `back-end/Dockerfile` 构建，Gunicorn 提供 DRF | 使用应用专用 `DB_USER` / `DB_PASSWORD` 访问 `mysql:3306` | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${BACKEND_HOST_PORT}`，API 固定追加 `/api/v1`。 |
| `backend-bootstrap` | 复用 backend 镜像，profile `bootstrap` 的一次性管理命令服务 | 仅固定 Job 的 schema 阶段访问 `mysql:3306` | 无常驻容器、无公开端口、无卷。 |
| `frontend` | `front-end/Dockerfile` 构建，Nginx 运行时镜像 | 通过 API 代理访问 backend | `${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${FRONTEND_HOST_PORT}`。 |
| `jenkins-sync-worker` | 复用 backend 镜像，执行 `sync_jenkins_results --watch` | 访问 `mysql:3306` 和 `jenkins:8080` | 无宿主机端口；以心跳 healthcheck 验证。 |
| `api-runner` | `api-test/Dockerfile` 构建 | 仅 Jenkins 以隔离容器方式运行 | 无常驻容器、无公开端口。 |

`api-runner` 使用 `tools profile`，只在 Jenkins 调度接口自动化或环境全量测试时按需运行；它不应由主人或 AI 当作常驻服务启动。

关键 Docker 文件：

| 文件 | 用途 |
| --- | --- |
| `docker-compose.yml` | 默认 Compose 服务、网络、volume 与 Jenkins 工具链镜像构建定义。 |
| `docker/jenkins/Dockerfile` | 默认 Jenkins tools 镜像构建来源。 |
| `back-end/Dockerfile` | backend 与 Jenkins 同步 worker 镜像构建来源。 |
| `front-end/Dockerfile` | frontend 运行与测试镜像构建来源。 |
| `api-test/Dockerfile` | api-runner 隔离测试镜像构建来源。 |

Jenkins controller 使用 Docker Socket 控制**应用服务**镜像和容器。环境 Job 在部署前记录 MySQL/Jenkins 容器 ID，部署后再次核对；基础服务在构建期间发生改变时会失败并保留诊断。因此环境 Job 从不启动、停止或重建 MySQL/Jenkins。

## 首次启动

### 1. 准备私有 `.env`

根目录 `.env` 是本地私有配置入口，不能提交 Git。**首次启动前先手工从 `.env.example` 创建并补齐 `.env`，再运行基础服务 bootstrap helper。** helper 即使能够在 `.env` 缺失时复制模板，也不会猜测或生成全部私有配置；复制后必须停止本次流程、人工补齐私有区，再重新运行。

仅在本地 `.env` 维护的 16 项私有配置如下；`.env.example` 不列出这些键，也不提供可用凭据占位：

| 私有配置 | 用途 |
| --- | --- |
| `MYSQL_ROOT_PASSWORD` | 仅用于 MySQL 管理、首次初始化和 healthcheck。 |
| `DB_USER`、`DB_PASSWORD` | backend、worker 和一次性 bootstrap 使用的应用专用非 root 数据库账号。 |
| `DJANGO_SECRET_KEY`、`AUTH_TOKEN_SECRET` | Django 与登录令牌签名密钥。 |
| `JENKINS_USERNAME`、`JENKINS_API_TOKEN` | backend/helper 调用本地 Jenkins API 的凭据；本地 Init Groovy 可由基础服务 helper 安全回填。 |
| `INITIAL_ADMIN_USERNAME`、`INITIAL_ADMIN_DISPLAY_NAME`、`INITIAL_ADMIN_PASSWORD` | 首次 bootstrap 管理员资料。 |
| `JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL`、`JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH` | 环境目录受控 SCM 来源。 |
| `JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID`、`JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID` | 环境目录 checkout 与 push 的独立 Jenkins Credentials ID。 |
| `JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID` | Jenkins 调用 backend 内部 API 时使用的 Secret Text Credentials ID。 |
| `JENKINS_API_TEST_E9_CREDENTIALS_ID` | 业务 API Job 使用的 Jenkins Secret Text Credentials ID；内容为 E9 角色账号 JSON，仅在 Jenkins 私有环境中配置。 |
| `ENVIRONMENT_CATALOG_SERVICE_TOKEN` | 注入 backend 的服务令牌；启用同步时必须与上一项所指 Jenkins Secret Text 的内容一致。 |

`DB_USER` 与 `DB_PASSWORD` 是 Compose **必填**的应用专用非 root 数据库用户和密码，**只写入本地 `.env`**。`MYSQL_ROOT_PASSWORD` 只用于 MySQL 管理和初始化，不作为 backend 或 worker 的应用连接账号。

可提交的 `.env.example` 只有以下 12 项公共配置，顺序、分组和注释必须与本地 `.env` 公共区一致，值可按部署环境不同：

| 配置类别 | 代表变量 | 用途 |
| --- | --- | --- |
| 平台网络 | `PLATFORM_BIND_HOST`、`PLATFORM_PUBLIC_HOST`、`PLATFORM_PUBLIC_SCHEME` | 控制宿主机监听和使用者看到的统一公开主机/协议。 |
| 宿主机端口 | `MYSQL_HOST_PORT`、`JENKINS_HTTP_PORT`、`JENKINS_AGENT_PORT`、`BACKEND_HOST_PORT`、`FRONTEND_HOST_PORT` | 控制五个对外端口；容器内部端口固定。 |
| 运维选项 | `PROJECT_WORKSPACE`、`DOCKER_GID`、`CI_RUN_RETENTION_DAYS`、`FRONTEND_PLAYWRIGHT_BASE_IMAGE` | 控制宿主机源码挂载、Socket 组、报告保留和前端测试镜像。 |

Jenkins、backend、frontend 的公开 URL 由 `PLATFORM_PUBLIC_SCHEME`、`PLATFORM_PUBLIC_HOST` 和对应端口统一派生，不再逐服务配置 URL。Vite 本地代理直连宿主机 backend 明文端口；Playwright 启动的本地 Vite webServer 固定使用 HTTP 与 4173 端口。两者从 `PLATFORM_BIND_HOST` 派生可连接地址（`0.0.0.0` 映射为 `127.0.0.1`，`::` 映射为 `::1`），不复用外部主机或 HTTPS 协议。

以下固定项不属于环境配置：Compose service name 与内部端口、固定 Job 名、Jenkins 40 executors、Pipeline/HTTP/轮询/心跳超时、容器内 `/workspace/AiApiTest-DWP`、API 路径 `/api/v1`、数据库名、时区和 Cookie 策略。登录 Cookie 固定为 `authToken`、8 小时、`SameSite=Lax`、路径 `/`；仅 `Secure` 根据 `PLATFORM_PUBLIC_SCHEME=https` 自动启用。

`PROJECT_WORKSPACE` 必须指向当前正在开发或验收的仓库根目录。它指向旧工作区时，Jenkins 会加载旧代码，即使当前分支已提交也不会生效。

### 2. 启动基础服务

Windows PowerShell：

```powershell
.\scripts\deploy-docker.ps1
```

Linux、macOS 或 Git Bash：

```bash
bash scripts/deploy-docker.sh
```

上述脚本会校验 Docker Compose、启动 `mysql` 与 `jenkins`，并等待本地 Jenkins Init Groovy 生成运行时 API 凭据。它们不启动 backend、frontend 或 worker。若 `.env` 意外缺失并由脚本复制模板，必须先补齐全部私有项，再重新运行脚本。

如需只执行基础服务 Compose 命令，主人或平台运维可执行：

```bash
docker compose up -d mysql jenkins
docker compose ps
```

等待 MySQL 为 `healthy`、Jenkins 页面可访问后，Jenkins 启动时幂等创建或修复代码固定的 Pipeline Job `AiApiTest-DWP-Platform-Bootstrap`。该名称不允许通过 `.env` 改写。

### 3. 构建平台应用环境

在 Jenkins 页面打开固定 Job 后点击 Build，默认参数即为全量应用重建和冒烟验收：

| 参数 | 默认值 | 行为 |
| --- | --- | --- |
| `build_all` | `true` | 重新构建三项应用镜像，并以 `--force-recreate` 重建 backend、frontend、worker。 |
| `run_full_tests` | `false` | 仅执行不依赖登录账号的健康与冒烟测试。 |

需要增量重建和全量回归时，将 `build_all=false`、`run_full_tests=true`。增量模式只复用镜像标签和完整性均满足的依赖域；服务缺失或构建输入发生变化时仍会重建。

也可以用 helper 触发同一 Jenkins Job，而不是在宿主机直接启动应用服务：

Windows PowerShell：

```powershell
# 默认：全量重建 + 冒烟
.\scripts\trigger-platform-bootstrap.ps1

# 增量检查 + 全量回归
.\scripts\trigger-platform-bootstrap.ps1 -BuildAll false -RunFullTests true
```

Linux、macOS 或 Git Bash：

```bash
# 默认：全量重建 + 冒烟
bash scripts/trigger-platform-bootstrap.sh

# 增量检查 + 全量回归
bash scripts/trigger-platform-bootstrap.sh --build-all false --run-full-tests true
```

helper 只通过 Jenkins API 提交并轮询固定 Job，使用相同的参数、阶段、日志和结果契约，不是本机启动旁路。

## 环境 Job 的八个阶段

| 阶段 | 做什么 | 失败后的处理 |
| --- | --- | --- |
| Checkout/Workspace | 使用代码固定的 `/workspace/AiApiTest-DWP` 挂载仓库获取流水线源码；环境目录同步 Job 才使用独立受管 SCM。 | 保留 Jenkins 控制台和可用证据。 |
| Bootstrap Preflight | 校验 `.env`、Docker CLI/Compose、Socket/GID、MySQL/Jenkins 运行状态以及 MySQL health。 | 输出结构化诊断并停止。 |
| Dependency Assurance | 分别校验 backend、frontend、api-runner 三个依赖域。缺失或不满足时各只安装/构建一次，完整记录日志。 | 汇总失败域，在部署前停止。 |
| Schema & Initial Data | 仅通过 profile `bootstrap` 的一次性 `backend-bootstrap` 服务依序执行 `migrate --noinput`、`seed_environment`、`init_admin --bootstrap-only`。空库创建全部 Django 表；已有库只应用未执行 migration。 | 任一步失败即阻止 Deploy；不 rollback、不清库、不删表。 |
| Deploy | 仅部署 backend、frontend、`jenkins-sync-worker`。 | 保留服务与部署日志；不回滚、不删除卷。 |
| Health | 探测 backend live/ready、frontend health/SPA/API 代理和 worker 心跳。 | 输出失败服务的结构化原因与证据。 |
| Tests | 默认执行公开健康与冒烟探针；全量模式还运行 backend pytest、frontend unit/build/Playwright、api-runner/Jenkins 静态测试。 | 归档已有测试证据并标记构建失败。 |
| Archive & Summary | 归档证据并发布可用的 Allure 结果。 | 即使前序失败也尽力生成 Summary 与归档。 |

环境 Job 仅在 `Schema & Initial Data` 通过一次性 `backend-bootstrap` 服务执行 `migrate --noinput`、`seed_environment`、`init_admin --bootstrap-only`；该服务无端口、卷、`container_name`、healthcheck、`depends_on` 或常驻 restart，且不属于 Deploy 的应用服务。AI、宿主机、常驻 backend/worker、readiness 和其他 Job 不执行 migration 或初始化管理员。所有路径继续禁止 `collectstatic`、自动 rollback、`down -v`、volume 删除、清库、删表或 reset。服务或依赖失败时，先阅读 Jenkins 的 Summary、结构化诊断和 Artifact，修复根因后重新构建。

## 访问平台与构建产物

环境 Job 成功后，从其 Summary 读取由公共主机、协议和端口派生的公开地址：

- Jenkins：`${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${JENKINS_HTTP_PORT}`
- 前端：`${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${FRONTEND_HOST_PORT}/platform`
- 后端 API 文档：`${PLATFORM_PUBLIC_SCHEME}://${PLATFORM_PUBLIC_HOST}:${BACKEND_HOST_PORT}/api/docs/`
- 测试证据和 Allure：当前 Jenkins Build 的 Artifact 与 Allure 入口

Allure 是 Jenkins Build 级插件和归档入口，不是额外常驻 Compose 服务。原始运行日志、报告、截图和测试证据只保留为 Jenkins Artifact，或在 `docs/` 临时目录短暂存放后清理，不提交 Git。

## 故障排查

| Jenkins 诊断或现象 | 处理方式 |
| --- | --- |
| `.env` 缺失、变量或公开地址错误 | 修正本地私有 `.env`，不要提交；重新构建固定 Job。 |
| Docker CLI、Compose、Socket 或 `DOCKER_GID` 不可用 | 修复 Jenkins 工具链镜像、Socket 挂载或 GID，然后由主人/平台运维重建 Jenkins bootstrap。 |
| MySQL 未运行或 `unhealthy` | 由主人/平台运维启动或修复 MySQL，等待 `healthy` 后重新构建。 |
| backend、frontend 或 api-runner 依赖构建失败 | 阅读对应依赖域完整安装日志，修复 Dockerfile、lockfile、镜像源或网络后重新构建；每次构建内不会重复安装。 |
| Health 超时 | 阅读 Job Health 阶段和相应服务日志，修复配置或应用逻辑后重新构建。 |
| helper 认证、固定 Job 或轮询超时 | 校验 `JENKINS_USERNAME`、`JENKINS_API_TOKEN` 和 Init Groovy 是否已创建固定 Job；helper 的请求/轮询/30 分钟总等待值由代码维护。 |
| Jenkins 加载旧代码 | 修正 `PROJECT_WORKSPACE`，保持它指向当前仓库；重建 Jenkins bootstrap 后再运行 Job。 |

### MySQL 密码不一致：

1. 确认私有 `.env` 中的 `MYSQL_ROOT_PASSWORD` 仅用于 MySQL 管理和初始化，同时已配置必填的 `DB_USER` 与 `DB_PASSWORD`。
2. backend 与 `jenkins-sync-worker` 的应用连接只使用 `DB_USER`、`DB_PASSWORD`；确认 MySQL 中存在匹配的应用专用非 root 数据库用户和密码。
3. 持久化数据卷已初始化后，修改 `.env` 不会自动更新 root 或应用用户密码。需要变更时由主人/平台运维在确认数据策略后同步凭据；环境 Job 不会删除数据卷。

## 环境 Job 创建与使用

固定 Job 由 Jenkins 启动时幂等创建或修复，不能在 Jenkins Script Console 手工创建旁路 Job。主人在 Jenkins 页面构建同一个 `AiApiTest-DWP-Platform-Bootstrap`，或使用 `scripts/trigger-platform-bootstrap.ps1`、`scripts/trigger-platform-bootstrap.sh` 触发同一契约。失败时先阅读 Jenkins 结构化诊断，修复后重新构建。

## 维护与安全边界

基础服务维护命令只供主人或平台运维使用：

```bash
docker compose ps
docker compose logs -f mysql
docker compose logs -f jenkins
docker compose down
```

`docker compose down` 会停止基础服务但保留命名数据卷。删除卷、`down -v`、`chmod 666 /var/run/docker.sock` 均不属于正常平台操作；执行数据清理前必须确认本地 Jenkins/MySQL 数据不再需要。

Docker Socket 使 Jenkins controller 具备主机级 Docker 控制能力，只适用于受信任的本地开发或验收 controller，不能用于不受信任的 SCM/PR Job。这不是生产部署安全承诺。Linux 应由主人/平台运维读取 Socket 实际组 ID 并写入私有 `.env` 的 `DOCKER_GID`；Windows Docker Desktop 使用的值也必须以实际环境验证。任何环境都禁止 `chmod 666 /var/run/docker.sock`。

AI 对 backend、frontend、worker 的重启、依赖检查/安装和环境验收必须且只能触发 `AiApiTest-DWP-Platform-Bootstrap`，或使用两个 helper 触发同一 Job。AI 不得直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、`pip install`、`npm install/npm ci`、Django `runserver`、Vite 或 worker 启动命令。

## 修改配置后的刷新

修改 `PROJECT_WORKSPACE` 或 Jenkins Init Groovy 后，主人/平台运维可保留 Jenkins 数据卷并重建 Jenkins 容器，使 Init Groovy 再次执行。固定 Job 名不可配置：

```bash
docker compose up -d --no-deps --force-recreate jenkins
```

之后确认固定 Job 已由启动初始化脚本创建或修复，再从 Jenkins 页面重新构建环境 Job。应用源代码、Dockerfile、前端或 api-test 依赖变化，不在 Jenkins controller、宿主机或运行容器内动态安装；使用 `build_all=true` 的环境 Job 统一重建。
