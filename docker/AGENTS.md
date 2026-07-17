# docker/AGENTS.md

本目录是本地容器和基础服务设计目录。进入 `docker/` 工作前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `docker/` 属于非循环基础设施阶段，不要求每个需求重复产出。
- 本目录负责当前 Docker Compose、Jenkins 工具链镜像、MySQL/Jenkins bootstrap、应用服务镜像定义、健康检查、部署说明和环境模板。
- 当前 Compose 已声明完整的平台服务载体；Docker 负责镜像、网络、volume 和容器运行，Jenkins Platform Bootstrap Job 负责应用服务环境的受控构建、部署、验收和证据归档。
- 整体 Docker 化不是把所有代码塞进单个巨大镜像，而是通过 Compose 编排多个职责清晰的服务容器。

## 当前 Compose 服务与控制边界

`docker-compose.yml` 当前声明的服务与镜像边界如下：

| 服务 | 当前容器职责 | 当前控制边界 |
| --- | --- | --- |
| `mysql` | 平台数据库，持久化 `aiapitest-mysql-data` | 主人/平台运维 bootstrap；应用通过 `mysql:3306` 访问。 |
| `jenkins` | Jenkins controller、工具链、Init Groovy 和 Docker Socket 客户端 | 主人/平台运维 bootstrap；启动时创建/修复固定 Job。 |
| `backend` | Gunicorn/DRF API | 仅由固定环境 Job 部署和重建。 |
| `frontend` | Vue 构建产物的 Nginx 运行时服务与 API 代理 | 仅由固定环境 Job 部署和重建；没有独立 `nginx` Compose 服务。 |
| `jenkins-sync-worker` | 复用 backend 镜像，同步 Jenkins 构建结果并提供心跳 | 仅由固定环境 Job 部署和重建。 |
| `api-runner` | pytest/Allure 隔离测试镜像 | `tools` profile，按 Jenkins 调度运行，不是常驻服务。 |

- 容器内部依赖使用 Compose 服务名，例如 `mysql:3306`、`jenkins:8080`、`backend:8000`；宿主机端口只作为外部访问入口。
- 所有运行数据通过 volume 保存，镜像只放可重建的应用代码和工具链；配置来自 `.env.example`、私有 `.env`、环境变量或 Jenkins Credentials。
- Docker Compose 技术上可以直接拉起应用容器，但这会绕过当前依赖完整性、镜像输入、Health、Tests 和 Jenkins artifact 门禁；它不是当前平台的标准使用方式，更不是 AI 的允许入口。

## 变更入口

- 当需求影响数据库服务、Jenkins 服务、本地联调环境、端口、卷挂载或初始化脚本时，才修改本目录。
- 修改前应确认架构说明、部署说明和相关模块需求是否需要同步更新。
- 如果容器变更会影响 DRF、Jenkins 或前端联调，需要在对应模块文档中说明依赖变化。
- 如果需求新增后端、前端、Jenkins 或 `api-test` 的运行依赖，应同步评估是否需要更新对应 Dockerfile、Compose 服务、健康检查和部署说明。

## 文件约定

- Compose 文件、初始化脚本和部署说明必须使用仓库相对路径。
- 示例配置使用 `.env.example`、占位符或环境变量，不提交真实 `.env`。
- 数据卷、日志、报告、缓存和本地数据库文件属于运行产物，不提交 git。
- 端口、服务名和网络名应保持通用，避免绑定个人机器路径。
- 后端和前端的 Dockerfile 可以放在各自模块目录，也可以由 `docker/` 统一管理；无论位置如何，都必须在本目录部署说明中写清楚构建入口。
- Compose 文件可以按用途拆分，例如基础服务、完整平台、CI 验证 override，但命名和启动命令必须清晰。

## 验证要求

- 修改 Compose 或初始化脚本后，应至少完成静态配置验证，并通过固定 Platform Bootstrap Job 验证应用服务部署、健康检查、冒烟或全量回归和归档证据。
- MySQL 相关变更要说明默认库名、用户占位符、字符集和迁移执行方式。
- Jenkins 相关变更要说明插件、凭据注入方式、workspace 挂载和 Job 初始化策略。
- 整体平台 Compose 变更要验证前端可访问、后端/worker 依赖可达、worker 心跳、Jenkins 可调度 `api-test` runner；这些环境验证必须在固定 Job 内完成。
- 镜像构建必须避免依赖个人本机绝对路径；需要挂载源码时应使用仓库根目录相对路径或 CI workspace。

## 安全要求

- 不提交真实账号、密码、token、cookie、Jenkins API Token、生产 URL 或敏感地址。
- 不把容器配置作为生产部署承诺；生产部署需要单独设计安全、备份、权限和网络策略。
- 不把 `.env`、Jenkins home、MySQL 数据、Allure 报告、运行日志或测试产物打进业务镜像。

## 平台环境唯一入口（强制）

- 平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，AI 必须且只能触发固定 Jenkins 环境 Job。
- 固定环境 Job 名为私有 `.env` 的 `JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME`，默认 `AiApiTest-DWP-Platform-Bootstrap`；它由本地 Compose Jenkins 启动时通过版本化 init Groovy 幂等创建或修复，固定加载 `jenkins/Jenkinsfile.platform-bootstrap`，不得手工创建另一条旁路 Job。
- 该 Job 固定经过七阶段：`Checkout/Workspace`、`Bootstrap Preflight`、`Dependency Assurance`、`Deploy`、`Health`、`Tests`、`Archive & Summary`。Docker 在其中是应用容器的运行载体，不是绕过 Job 的第二条环境入口。
- Windows 唯一入口为 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash 唯一入口为 `scripts/trigger-platform-bootstrap.sh`。用户在 Jenkins 页面手工点击同一 Job 也使用相同 Pipeline、参数、阶段和结果契约。
- AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install/npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 替代环境 Job。
- MySQL 与 Jenkins 仅由主人/平台运维按 `docker/DEPLOYMENT.md` 完成 bootstrap；环境 Job/helper 永不管理这两个基础服务。AI 只能检查并反馈，不能代替主人/平台运维启动。
- 禁止 `down -v`、volume 删除、`chmod 666 /var/run/docker.sock`、migration、初始化管理员、`collectstatic`、自动 rollback 或输出真实凭据。环境失败必须阅读 Jenkins 结构化诊断，引导主人修复后重新构建，不能旁路处理。
