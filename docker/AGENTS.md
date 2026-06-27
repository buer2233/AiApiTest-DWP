# docker/AGENTS.md

本目录是本地容器和基础服务设计目录。进入 `docker/` 工作前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `docker/` 属于非循环基础设施阶段，不要求每个需求重复产出。
- 本目录负责本地 MySQL、Jenkins 等基础服务的 Docker Compose、初始化脚本、部署说明和环境模板。
- 当前阶段容器主要服务本地开发、联调和 CI 验证；后期必须支持把整个平台作为一个 Docker Compose 项目整体打包部署。
- 整体 Docker 化不是把所有代码塞进单个巨大镜像，而是通过 Compose 编排多个职责清晰的服务容器。

## 后期整体 Docker 化预案

后期需要支持一条命令启动完整测试平台：

```text
docker compose up -d
```

目标服务边界：

| 服务 | 建议容器职责 | 关键要求 |
| --- | --- | --- |
| `mysql` | 平台数据库 | 使用持久化 volume，后端通过 `mysql:3306` 访问 |
| `jenkins` | Jenkins controller 和执行主干 | 固化插件、Job 模板、JCasC 或初始化脚本，不手工配置关键 Job |
| `backend` | DRF API 服务 | 使用环境变量连接 MySQL 和 Jenkins，不写死宿主机地址 |
| `frontend` | Vue 3 构建后的静态资源 | 构建产物由 Nginx 或静态服务承载 |
| `nginx` | 平台统一入口和反向代理 | 统一转发 `/api`、前端静态资源和可选 Jenkins/报告入口 |
| `api-runner` 或 Jenkins agent | pytest、Allure、`api-test` 执行环境 | Jenkins 调度执行，不绕过 Jenkins 主干 |

推荐落地顺序：

1. 保留当前 `mysql`、`jenkins` 基础服务 Compose。
2. 为 `back-end/` 增加后端镜像，支持迁移、健康检查和 `gunicorn` 启动。
3. 为 `front-end/` 增加多阶段构建镜像，输出 Vue 静态资源。
4. 固化 Jenkins 工具链、插件、凭据占位符、Job DSL 或 JCasC 初始化策略。
5. 将 `api-test` 执行环境抽象为 runner 镜像或 Jenkins agent，而不是长期常驻业务服务。
6. 增加 `nginx` 统一入口，并明确报告、静态资源和 API 的访问路径。

整体容器化必须满足：

- 服务间通信使用 Compose 服务名，例如 `mysql:3306`、`jenkins:8080`、`backend:8000`。
- 宿主机端口只作为外部访问入口，不作为容器内部依赖地址。
- 所有运行数据通过 volume 保存，镜像内只放可重建的应用代码和工具链。
- Jenkins 仍是测试执行唯一主干；DRF 不因为容器化而直接执行 pytest。
- `api-test` 的执行协议仍只在 `api-test/tools/ci_runner.py` 演进。
- 配置通过 `.env.example`、环境变量、Jenkins Credentials 或本地私有文件注入。

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

- 修改 Compose 或初始化脚本后，应至少验证服务能启动、健康检查通过、关键端口可访问。
- MySQL 相关变更要说明默认库名、用户占位符、字符集和迁移执行方式。
- Jenkins 相关变更要说明插件、凭据注入方式、workspace 挂载和 Job 初始化策略。
- 整体平台 Compose 变更要验证前端可访问、后端健康检查通过、后端可访问 MySQL、后端可访问 Jenkins、Jenkins 可调度 `api-test` runner。
- 镜像构建必须避免依赖个人本机绝对路径；需要挂载源码时应使用仓库根目录相对路径或 CI workspace。

## 安全要求

- 不提交真实账号、密码、token、cookie、Jenkins API Token、生产 URL 或敏感地址。
- 不把容器配置作为生产部署承诺；生产部署需要单独设计安全、备份、权限和网络策略。
- 不把 `.env`、Jenkins home、MySQL 数据、Allure 报告、运行日志或测试产物打进业务镜像。
