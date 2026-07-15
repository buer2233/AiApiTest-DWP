# Docker Deployment

本文档是本项目 Docker bootstrap 的详细说明，只面向主人/平台运维。AI 不执行本文件的 Docker 命令；AI 的平台应用环境操作只能触发固定 Jenkins 环境 Job。

## 部署目标

当前 `docker-compose.yml` 声明以下默认 Compose 服务。MySQL 与 Jenkins 是用户管理的 bootstrap 基础服务；其余应用服务的构建、依赖检查、启动、健康检查与环境验收均由 Jenkins 环境 Job 管理，不能以宿主机命令替代。

## 关键文件

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 默认 Compose 服务与 Jenkins 工具链镜像构建定义 |
| `docker-compose.jenkins-tools.yml` | 与默认工具镜像一致的兼容 overlay，不是环境 Job 的必需入口 |
| `.env.example` | 可提交的通用网络配置模板 |
| `.env` | 本地私有部署配置，不提交 git |
| `scripts/deploy-docker.ps1` | Windows PowerShell 一键部署脚本 |
| `scripts/deploy-docker.sh` | Linux/macOS/Git Bash 一键部署脚本 |
| `docker/jenkins/Dockerfile` | 默认 Jenkins tools 镜像构建来源 |

## 默认 Compose 服务

| 服务 | 角色 | 生命周期 |
|------|------|----------|
| `mysql` | DRF 数据库 | 主人/平台运维 bootstrap；持久化 `aiapitest-mysql-data` |
| `jenkins` | Jenkins controller | 主人/平台运维 bootstrap；持久化 `aiapitest-jenkins-home` |
| `backend` | DRF API | Jenkins 环境 Job 管理 |
| `frontend` | 前端/Nginx 服务 | Jenkins 环境 Job 管理 |
| `jenkins-sync-worker` | Jenkins 结果同步 worker | Jenkins 环境 Job 管理 |
| `api-runner` | pytest/Allure 隔离执行镜像 | `tools profile`，非常驻服务，由 Jenkins 调度 |

默认 Jenkins controller 构建 `docker/jenkins/Dockerfile` 工具链镜像 `aiapitest-jenkins:lts-jdk17-tools`，不是可选 override。该镜像提供 Docker CLI/Compose、Allure 与 Jenkins 插件；业务 pytest/Allure 依赖仍只在 `aiapitest-api-runner:local` 镜像构建阶段安装。

Jenkins 访问地址：

由 `.env` 中 `JENKINS_PUBLIC_BASE_URL` 决定。

MySQL 本机连接：

由 `.env` 中 `MYSQL_BIND_HOST`、`MYSQL_HOST_PORT`、`MYSQL_DATABASE` 和后端数据库用户变量决定。

## 人工部署

> **仅主人/平台运维执行，AI 不得执行。** 本节命令仅用于启动或维护 MySQL/Jenkins bootstrap 容器；环境 Job/helper 永不管理 MySQL 与 Jenkins。

部署前确认 Docker Compose 可用：

```bash
docker compose version
```

Windows PowerShell：

```powershell
.\scripts\deploy-docker.ps1
```

Linux/macOS/Git Bash：

```bash
bash scripts/deploy-docker.sh
```

脚本会在缺少 `.env` 时从 `.env.example` 创建本地配置。`.env.example` 只包含 IP、端口和服务入口；首次启动前必须在本地 `.env` 中补齐 `MYSQL_ROOT_PASSWORD`、`DB_USER`、`DB_PASSWORD`、初始化管理员账号、Django/Auth 密钥等私有配置。

补齐 `.env` 后执行：

```bash
docker compose up -d mysql jenkins
```

首次部署建议检查 `.env` 的通用网络配置：

```text
MYSQL_HOST_PORT=3307
JENKINS_PUBLIC_BASE_URL=http://localhost:8080
JENKINS_HTTP_PORT=8080
JENKINS_AGENT_PORT=50001
JENKINS_EXECUTORS=40
JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME=AiApiTest-DWP-Platform-Bootstrap
PROJECT_WORKSPACE=$PROJECT_ROOT
CI_RUN_RETENTION_DAYS=30
DOCKER_GID=0
BACKEND_BIND_HOST=127.0.0.1
BACKEND_HOST_PORT=8000
FRONTEND_BIND_HOST=127.0.0.1
FRONTEND_HOST_PORT=5173
JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS=60
```

同时在 `.env` 中维护私有配置，例如 `MYSQL_ROOT_PASSWORD`、`DB_USER`、`DB_PASSWORD`、`DJANGO_SECRET_KEY`、`AUTH_TOKEN_SECRET`、`INITIAL_ADMIN_USERNAME` 和 `INITIAL_ADMIN_PASSWORD`。其中 `DB_USER` 与 `DB_PASSWORD` 是 Compose 必填的应用专用非 root 数据库用户和密码，只写入本地 `.env`；`MYSQL_ROOT_PASSWORD` 只用于 MySQL 管理和初始化，不作为 backend 或 worker 的运行连接账号。

## AI 环境操作边界

AI 对平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，必须且只能触发同一 Jenkins 环境 Job：

- Windows：`scripts/trigger-platform-bootstrap.ps1`
- Linux/macOS/Git Bash：`scripts/trigger-platform-bootstrap.sh`

AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install`、`npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 来替代环境 Job。MySQL/Jenkins 未运行、Docker Socket 不可用或配置缺失时，AI 只能报告 Jenkins 结构化诊断，引导主人/平台运维修复后重新构建，不能旁路修复。

## 后端连接 Docker MySQL

后端本地运行默认读取仓库根目录 `.env`，正式 Compose 运行时 backend 与 `jenkins-sync-worker` 固定使用本地 `.env` 中必填的 `DB_USER`、`DB_PASSWORD` 连接 `mysql:3306`。`MYSQL_ROOT_PASSWORD` 仅供 MySQL 管理和初始化；宿主机调试连接地址仍由 `MYSQL_BIND_HOST` 与 `MYSQL_HOST_PORT` 决定。这些私有账号、密码和数据库名不写入 `.env.example`，模板只保留变量用途说明。

测试环境仍由 `config.settings.test` 使用内存 SQLite，不依赖本机 MySQL。

## Jenkins 初始配置

查看 Jenkins 初始管理员密码：

```bash
docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

该密码只用于本地首次初始化，不要提交到仓库或写入项目文档。

Jenkins 初始化后，既有业务 Pipeline job 可使用仓库中的：

```text
jenkins/Jenkinsfile
```

默认 Compose 会把版本化的 `jenkins/scripts/configure-local-mounted-jobs.groovy` 挂载到 `init.groovy.d`。Jenkins 启动时幂等创建或修复 `AiApiTest-DWP-Platform-Bootstrap` 环境 Job，以及各模块 Daily Job；环境 Job 无 cron、固定加载 `jenkins/Jenkinsfile.platform-bootstrap`，Daily Job 配置凌晨 2 点定时器，并停用遗留共享 Daily Job 的定时器。无需在 Script Console 手工粘贴脚本。模块配置变化后可由主人/平台运维使用以下命令重新加载初始化脚本，保留 Jenkins home 数据卷：

```bash
docker compose up -d --no-deps --force-recreate jenkins
```

Stage13 Compose 已定义 `backend`、`frontend` 和 `jenkins-sync-worker` 应用服务。它们只能由环境 Job 部署；worker 从运行时环境读取数据库与 Jenkins 配置，容器内部通过 `mysql:3306` 和 `jenkins:8080` 访问依赖，不绑定宿主机固定端口。

## Jenkins 工具链镜像

默认 `docker-compose.yml` 已构建 Jenkins 工具链镜像，首次 bootstrap 或工具链镜像变更时由主人/平台运维执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins-tools.yml up -d mysql jenkins
```

默认 Compose 的 Jenkins build 会构建 `docker/jenkins/Dockerfile`，额外安装：

- `python3`
- `python3-pip`
- `python-is-python3`
- `git`
- Docker CLI、Buildx 与 Compose plugin
- Allure CLI
- Jenkins Allure 插件

工具链镜像还会初始化 `/workspace` 目录权限，保证 Jenkins 用户能创建 `@tmp` 控制目录，并通过 init 脚本把镜像内 Allure CLI 注册为 Jenkins 全局工具 `Allure Commandline`。controller 不创建业务 venv、不安装 pytest/Allure 业务依赖；`api-test` 依赖只在固定 `aiapitest-api-runner:local` 镜像构建阶段安装，并由环境 Job 统一检查。

修改应用或 `api-test` 依赖后，不在 controller 或宿主机执行动态安装；使用环境 Job 的 `build_all=true` 重新构建镜像和应用服务。工具链镜像自身变更时，由主人/平台运维按本节 bootstrap 命令重建 Jenkins，不删除 Jenkins 数据卷。

Jenkins Pipeline 的本地报告会生成在挂载仓库的 `api-test/runtime/ci-runs/<run_id>/`。`PROJECT_WORKSPACE` 必须指向当前正在验收的仓库根目录；如果它指向旧工作区，Jenkins 会把报告写到旧工作区或容器临时目录，当前仓库下不会出现报告。`CI_RUN_RETENTION_DAYS` 默认 30，只清理超过保留期的历史 run 目录。

## 主人/平台运维维护命令

> **仅主人/平台运维执行，AI 不得执行。** 以下命令维护 bootstrap 服务，不是平台应用环境的启动入口。

查看服务：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f jenkins
docker compose logs -f mysql
```

停止服务但保留数据：

```bash
docker compose down
```

清理服务和数据卷：

```bash
docker compose down -v
```

执行清理数据卷前必须确认不再需要本地 Jenkins/MySQL 数据。AI 禁止 `down -v`、volume 删除和 `chmod 666 /var/run/docker.sock`。

## Bootstrap 故障处理

> **仅主人/平台运维执行，AI 不得执行。** 修复 bootstrap 故障后，回到 Jenkins 环境 Job 重新构建，不以宿主机应用命令绕过。

端口被占用：

1. 修改 `.env` 中的 `MYSQL_HOST_PORT`、`JENKINS_HTTP_PORT` 或 `JENKINS_AGENT_PORT`。
2. 重新执行一键部署脚本。
3. 如果 Jenkins 已初始化或已被后端记录任务链接，修改 `JENKINS_PUBLIC_BASE_URL` 前需要确认历史链接是否仍可访问。

同名容器已存在：

1. 先运行 `docker compose ps` 和 `docker ps -a` 确认容器来源。
2. 如果是本项目旧容器，可执行 `docker compose up -d mysql jenkins` 复用。
3. 如果是手工创建的冲突容器，先和用户确认是否停止或改名。

MySQL 密码不一致：

1. 确认 `.env` 中 `MYSQL_ROOT_PASSWORD` 仅用于 MySQL 管理和初始化，同时已配置必填的 `DB_USER` 与 `DB_PASSWORD`。
2. backend 与 `jenkins-sync-worker` 的应用连接只使用 `DB_USER`、`DB_PASSWORD`；确认 MySQL 中存在与之匹配的应用专用非 root 数据库用户和密码。
3. 已初始化过的持久化数据卷不会因为修改 `.env` 自动更新 root 或应用用户密码；必要时由主人/平台运维进入 MySQL 同步凭据，只有确认数据可删除后才允许重建数据卷。

## 环境 Job 创建与使用

完成 MySQL/Jenkins bootstrap 后，版本化 init Groovy 会在 Jenkins 启动时幂等创建或修复固定 Pipeline Job `AiApiTest-DWP-Platform-Bootstrap`，并与私有 `.env` 的 `JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME` 保持一致。该 Job 固定加载 `jenkins/Jenkinsfile.platform-bootstrap`、注入 `LOCAL_WORKSPACE_REPO=true`、无 cron，详细契约见 `jenkins/README.md`。

确认 Job 已由启动初始化脚本创建或修复后，用户可在 Jenkins 页面点击 Build，或使用两个 helper 触发同一契约：Windows 使用 `scripts/trigger-platform-bootstrap.ps1`，Linux/macOS/Git Bash 使用 `scripts/trigger-platform-bootstrap.sh`。构建完成后在 Jenkins Build Summary、归档产物、Allure 入口和 `.env` 配置的公开地址查看结果。

## Docker Socket 安全边界

Jenkins controller 挂载 `/var/run/docker.sock` 后拥有主机级 Docker 控制能力；`DOCKER_GID/group_add` 仅用于授权，不提供隔离。这只适用于受信任的本地开发/验收 controller，不是生产部署安全承诺，绝不允许不受信任 SCM/PR Job 使用该 Socket。

Linux 由主人/平台运维执行 `stat -c '%g' /var/run/docker.sock` 获取实际 GID，写入私有 `.env` 的 `DOCKER_GID` 后重建 Jenkins。Windows Docker Desktop 当前使用 `DOCKER_GID=0` 兼容值，必须由实际环境验证；任何平台都禁止 `chmod 666 /var/run/docker.sock`。

## 环境 Job 失败诊断

环境 Job 的失败摘要和结构化诊断是唯一应用环境排查入口。修复后重新构建：

| 诊断场景 | 主人/平台运维修复动作 |
| --- | --- |
| `.env` 缺失或公开地址/端口配置错误 | 在私有 `.env` 补齐或修正配置，不提交该文件，然后重新构建。 |
| Docker CLI、Compose 或 Socket/GID 不可用 | 修复 Jenkins 工具链镜像、Socket 挂载或 `DOCKER_GID`，重建 Jenkins bootstrap 后重新构建。 |
| MySQL 未运行或不健康 | 启动或修复 MySQL bootstrap 容器，等待 healthy 后重新构建。 |
| 依赖或镜像 build 失败 | 查看 Jenkins 对应依赖域日志；修复 Dockerfile/lockfile/网络或镜像源后重新构建。每个域只尝试一次安装。 |
| 应用 health 超时 | 查看 Jenkins 健康阶段与服务日志，修复配置或应用后重新构建；失败服务和证据会保留。 |
| helper 认证、Job 名或等待超时 | 校验 Jenkins Credentials、`JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME` 和 timeout 配置，修复后重新构建。 |

环境 Job 默认 `build_all=true`：重建镜像并重启全部应用服务；传入 `build_all=false` 时仅在缺失或构建输入变化时增量重建。默认执行冒烟测试，传入 `run_full_tests=true` 才执行平台全量测试。三个依赖域各自检查，缺失或不满足时只执行一次安装并输出成功/失败日志；任一失败会汇总后终止部署。环境 Job 不执行 migration、初始化管理员、`collectstatic`、rollback 或 volume 删除，失败时保留应用服务与证据。

启动后不建议修改的配置包括 MySQL/Jenkins volumes、数据库私有配置、Jenkins 公共 URL/Job 名、Compose project `aiapitest-dwp`、Socket/GID、认证 secret 与 Cookie 策略。Allure 是 Jenkins Build 级插件/归档入口，不新增常驻服务；公开链接由 `.env` 与 Jenkins runtime 生成。
