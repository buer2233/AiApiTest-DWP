# Docker Deployment

本文档是本项目 Docker 快速部署的详细说明，面向人工部署和 AI 自动部署。

## 部署目标

通过 Docker Compose 快速启动当前项目依赖的两个基础服务：

- MySQL：后端 DRF 使用的本地数据库。
- Jenkins：执行和管理接口自动化 Pipeline。

默认不包含 `back-end`、`front-end` 和 `api-test` 应用容器。这三个模块仍按项目阶段文档在本机或 Jenkins workspace 中运行。

## 关键文件

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 默认 MySQL 和 Jenkins 服务定义 |
| `docker-compose.jenkins-tools.yml` | 可选 Jenkins 工具链镜像 override |
| `.env.example` | 本地部署配置模板 |
| `.env` | 本地私有部署配置，不提交 git |
| `scripts/deploy-docker.ps1` | Windows PowerShell 一键部署脚本 |
| `scripts/deploy-docker.sh` | Linux/macOS/Git Bash 一键部署脚本 |
| `docker/jenkins/Dockerfile` | 可选 Jenkins 工具链镜像定义 |

## 默认服务

| 服务 | 镜像 | 容器名 | 主机端口 | 容器端口 | 数据卷 |
|------|------|--------|----------|----------|--------|
| MySQL | `mysql:8.4` | `aiapitest-mysql` | `127.0.0.1:3307` | `3306` | `aiapitest-mysql-data` |
| Jenkins | `jenkins/jenkins:lts-jdk17` | `aiapitest-jenkins` | `8080`, `50001` | `8080`, `50000` | `aiapitest-jenkins-home` |

Jenkins 访问地址：

```text
http://localhost:8080
```

MySQL 本机连接：

```text
host=127.0.0.1
port=3307
database=ai_api_test_platform
user=root
```

## 人工部署

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

脚本会在缺少 `.env` 时从 `.env.example` 创建本地配置，然后执行：

```bash
docker compose up -d mysql jenkins
```

首次部署建议检查 `.env`：

```text
MYSQL_ROOT_PASSWORD=change-me-local-root-password
MYSQL_PASSWORD=change-me-local-root-password
MYSQL_HOST_PORT=3307
JENKINS_HTTP_PORT=8080
JENKINS_AGENT_PORT=50001
```

`MYSQL_ROOT_PASSWORD` 和 `MYSQL_PASSWORD` 在默认 root 连接方式下应保持一致。

## AI 部署

如果让 AI 执行部署，建议给 AI 以下指令：

```text
请先读取 AGENTS.md 和 docker/DEPLOYMENT.md，然后使用仓库内 Docker Compose 脚本部署本项目依赖的 MySQL 和 Jenkins。不要提交 .env，不要删除已有数据卷；如果端口或同名容器冲突，先说明冲突并给出处理建议。
```

AI 执行时必须遵守：

1. 先运行 `git status --short`，确认工作区改动范围。
2. 运行 `docker compose version`，确认 Docker Compose 可用。
3. 优先使用 `scripts/deploy-docker.ps1` 或 `scripts/deploy-docker.sh`。
4. 不读取、不记录、不提交 `.env` 中的真实密码。
5. 不执行 `docker compose down -v`，除非用户明确要求删除本地数据。
6. 如果已有同名容器或端口冲突，先向用户说明再处理。

部署后验证：

```bash
docker compose ps
docker compose logs --tail=80 mysql
docker compose logs --tail=80 jenkins
```

## 后端连接 Docker MySQL

后端本地运行时需要使用和 `.env` 对齐的环境变量。

Windows PowerShell：

```powershell
$env:MYSQL_DATABASE="ai_api_test_platform"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="<和 .env 中 MYSQL_ROOT_PASSWORD 相同>"
$env:MYSQL_PORT="3307"
```

Linux/macOS/Git Bash：

```bash
export MYSQL_DATABASE=ai_api_test_platform
export MYSQL_USER=root
export MYSQL_PASSWORD="<和 .env 中 MYSQL_ROOT_PASSWORD 相同>"
export MYSQL_PORT=3307
```

如果把 `.env` 中 `MYSQL_HOST_PORT` 改为 `3306`，后端 `MYSQL_PORT` 也要同步改为 `3306`。

## Jenkins 初始配置

查看 Jenkins 初始管理员密码：

```bash
docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

该密码只用于本地首次初始化，不要提交到仓库或写入项目文档。

Jenkins 初始化后，创建 Pipeline job 时可使用仓库中的：

```text
jenkins/Jenkinsfile
```

## 可选 Jenkins 工具链镜像

默认 `docker-compose.yml` 使用官方 Jenkins 镜像，启动最快。

如果希望 Jenkins 容器内直接具备执行 `api-test` Pipeline 的工具链，可使用：

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins-tools.yml up -d mysql jenkins
```

该 override 会构建 `docker/jenkins/Dockerfile`，额外安装：

- `python3`
- `python3-pip`
- `python3-venv`
- `git`
- Allure CLI

注意：该构建需要访问 Debian 软件源和 Allure 下载地址，网络较慢时可能耗时较长。默认快速部署不依赖该构建。

## 常用命令

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

执行清理数据卷前必须确认不再需要本地 Jenkins/MySQL 数据。

## 故障处理

端口被占用：

1. 修改 `.env` 中的 `MYSQL_HOST_PORT`、`JENKINS_HTTP_PORT` 或 `JENKINS_AGENT_PORT`。
2. 重新执行一键部署脚本。

同名容器已存在：

1. 先运行 `docker compose ps` 和 `docker ps -a` 确认容器来源。
2. 如果是本项目旧容器，可执行 `docker compose up -d mysql jenkins` 复用。
3. 如果是手工创建的冲突容器，先和用户确认是否停止或改名。

MySQL 密码不一致：

1. 确认 `.env` 中 `MYSQL_ROOT_PASSWORD`。
2. 确认后端运行环境中的 `MYSQL_PASSWORD`。
3. 已初始化过的数据卷不会因为修改 `.env` 自动改 root 密码；必要时需要人工进入 MySQL 修改密码，或在确认可删除数据后重建数据卷。
