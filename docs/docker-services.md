# Docker Services

本文档记录本项目 MySQL 和 Jenkins 的 Docker Compose 部署方式。

## 服务来源

当前本机运行容器已反查为：

| 服务 | 镜像 | 容器名 | 端口 | 数据卷 |
|------|------|--------|------|--------|
| Jenkins | `jenkins/jenkins:lts-jdk17` | `aiapitest-jenkins` | `8080:8080`, `50001:50000` | `aiapitest-jenkins-home:/var/jenkins_home` |
| MySQL | `mysql:8.4` | `aiapitest-mysql` | `127.0.0.1:3307:3306` | `aiapitest-mysql-data:/var/lib/mysql` |

Compose 文件保留相同容器名、端口默认值和卷名，便于迁移到其他机器后快速启动。

## 一键启动

Windows PowerShell:

```powershell
.\scripts\deploy-docker.ps1
```

Linux/macOS/Git Bash:

```bash
bash scripts/deploy-docker.sh
```

脚本会在缺少 `.env` 时从 `.env.example` 创建一份本地配置，然后执行：

```bash
docker compose up -d mysql jenkins
```

## 配置

`.env.example` 只提供占位符。部署到新机器后复制为 `.env`，至少修改：

```text
MYSQL_ROOT_PASSWORD=change-me-local-root-password
```

默认端口：

```text
MYSQL_HOST_PORT=3307
JENKINS_HTTP_PORT=8080
JENKINS_AGENT_PORT=50001
```

后端本地运行时需要使用相同数据库配置：

```powershell
$env:MYSQL_DATABASE="ai_api_test_platform"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="<和 .env 中 MYSQL_ROOT_PASSWORD 相同>"
$env:MYSQL_PORT="3307"
```

如果目标机器希望后端使用 `localhost:3306`，可把 `.env` 中 `MYSQL_HOST_PORT` 改为 `3306`，同时把后端 `MYSQL_PORT` 环境变量改为 `3306`。

## Jenkins 运行环境

默认 `docker-compose.yml` 使用官方 `jenkins/jenkins:lts-jdk17`，这样新机器能最快启动 Jenkins 服务。

如果希望 Jenkins 容器内直接具备执行 `api-test` Pipeline 的工具链，可以使用可选 override：

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins-tools.yml up -d mysql jenkins
```

`docker/jenkins/Dockerfile` 基于官方 `jenkins/jenkins:lts-jdk17`，额外安装：

- `python3`
- `python3-pip`
- `python3-venv`
- `git`
- Allure CLI

这样 Jenkins Pipeline 可以直接在容器里执行本仓库 `api-test/tools/ci_runner.py`。该镜像构建需要访问 Debian 软件源和 Allure 下载地址，网络较慢时建议先用默认 Compose 拉起服务。

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

查看 Jenkins 初始密码：

```bash
docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

停止服务但保留数据：

```bash
docker compose down
```

清理服务和数据卷前必须确认不再需要本地 Jenkins/MySQL 数据：

```bash
docker compose down -v
```
