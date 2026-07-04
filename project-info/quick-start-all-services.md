# 当前项目所有服务快速启动说明

## 目标

本文档用于在本机快速启动当前 CICD AI 自动化测试平台的全部开发服务，并完成一次浏览器登录验收。

启动范围：

- Docker MySQL：后端 DRF 正式运行数据库。
- Docker Jenkins：本地 Jenkins 服务，用于后续 Pipeline 配置和任务触发。
- DRF 后端：提供登录、用户权限、Jenkins 查询和 Allure 报告入口 API。
- Vue 3 前端：测试平台界面。
- Playwright 浏览器验证：登录进入测试平台首页。

本文档只引用根目录 `.env` / `.env.example` 的变量名，不记录真实密码、token、Jenkins API Token、Cookie 或生产地址。真实 `.env` 属于本地私有配置，不提交 git。

## 前置条件

在项目根目录执行命令，以下示例用 `$PROJECT_ROOT` 表示仓库根目录：

```powershell
cd $PROJECT_ROOT
```

确认以下工具可用：

```powershell
docker compose version
python --version
node --version
npm --version
```

首次运行前复制通用网络配置模板：

```powershell
Copy-Item .env.example .env
```

`.env.example` 只保留 IP、端口和服务入口等通用配置。然后按本机情况修改 `.env`，并补齐仅存在于私有 `.env` 的账号、密码和密钥。必须重点确认：

- `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD`
- `MYSQL_BIND_HOST` / `MYSQL_HOST_PORT`
- `JENKINS_PUBLIC_BASE_URL`
- `BACKEND_SERVICE_URL`
- `FRONTEND_SERVICE_URL`
- `FRONTEND_DEV_HOST` / `FRONTEND_DEV_PORT`
- `FRONTEND_DEV_API_PROXY_TARGET`
- `VITE_API_BASE_URL`
- `INITIAL_ADMIN_USERNAME`
- `INITIAL_ADMIN_DISPLAY_NAME`
- `INITIAL_ADMIN_PASSWORD`

`MYSQL_DATABASE`、`DJANGO_SECRET_KEY`、`AUTH_TOKEN_SECRET`、`AUTH_COOKIE_*`、`INITIAL_ADMIN_*` 等属于固定默认项或私有配置，不写入 `.env.example`，但本地验收 `.env` 必须包含实际值。

## 启动后不建议修改的配置

以下配置一旦产生数据或被前后端/Jenkins 引用，修改前必须先评估迁移和回归成本：

| 配置 | 原因 |
| --- | --- |
| `MYSQL_DATABASE` | 改名会切换数据库，需要重新迁移或导入数据 |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | 旧 MySQL 数据卷不会因为 `.env` 改密自动更新 |
| `MYSQL_HOST_PORT` | 后端连接、文档和本地客户端都依赖该端口 |
| `JENKINS_PUBLIC_BASE_URL` | Jenkins 初始化、任务链接和后端记录可能依赖该地址 |
| `JENKINS_AGENT_PORT` | Jenkins agent 连接依赖该端口 |
| `PROJECT_WORKSPACE` | Jenkins 挂载路径和归档路径依赖该位置 |
| `AUTH_TOKEN_SECRET` | 轮换会使已有登录态失效 |
| `AUTH_COOKIE_*` | 会影响浏览器 Cookie 行为，需要和前端地址、HTTPS 策略一起验证 |

## 1. 启动 Docker MySQL 和 Jenkins

Windows PowerShell：

```powershell
.\scripts\deploy-docker.ps1
```

脚本会在 `.env` 不存在时从 `.env.example` 创建本地配置，然后执行：

```powershell
docker compose up -d mysql jenkins
```

查看服务状态：

```powershell
docker compose ps
docker compose logs --tail=80 mysql
docker compose logs --tail=80 jenkins
```

查看 Jenkins 首次初始化密码：

```powershell
docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

该密码只用于本地 Jenkins 首次初始化，不要写入项目文档或提交。

## 2. 启动 DRF 后端

后端默认读取仓库根目录 `.env`，正式运行使用 Docker MySQL。测试配置 `config.settings.test` 仍使用内存 SQLite，不依赖本机 MySQL。

安装依赖：

```powershell
cd $PROJECT_ROOT\back-end
python -m pip install -r requirements.txt
```

执行数据库迁移：

```powershell
python manage.py migrate
```

初始化本地验收管理员账号：

```powershell
python manage.py init_admin
```

启动后端：

```powershell
python manage.py runserver
```

后端接口文档地址由 `.env` 中 `BACKEND_SERVICE_URL` 派生：

```text
${BACKEND_SERVICE_URL}/api/docs/
```

## 3. 启动 Vue 3 前端

另开一个 PowerShell 窗口：

```powershell
cd $PROJECT_ROOT\front-end
npm install
npm run dev
```

前端开发服务会从根 `.env` 读取 `FRONTEND_DEV_HOST`、`FRONTEND_DEV_PORT` 和 `FRONTEND_DEV_API_PROXY_TARGET`。访问入口由 `FRONTEND_SERVICE_URL` 决定，默认路径为：

```text
${FRONTEND_SERVICE_URL}/platform
```

## 4. 登录验收

浏览器打开：

```text
${FRONTEND_SERVICE_URL}/platform
```

未登录时应自动跳转到登录页。输入本地 `.env` 中的：

```text
INITIAL_ADMIN_USERNAME
INITIAL_ADMIN_PASSWORD
```

登录成功后应进入测试平台，并看到模块通过率、失败用例、Jenkins 入口和 Allure 报告入口相关界面。

## 5. Playwright 验证步骤

Playwright webServer、baseURL 和权限 origin 由根 `.env` 中 `PLAYWRIGHT_WEB_SERVER_HOST`、`PLAYWRIGHT_WEB_SERVER_PORT`、`PLAYWRIGHT_BASE_URL` 派生。

```powershell
cd $PROJECT_ROOT\front-end
npm run test:e2e
```

验收通过标准：

- Jenkins 容器处于 running 或 healthy 状态。
- MySQL 容器处于 healthy 状态。
- 后端 `${BACKEND_SERVICE_URL}/api/docs/` 可访问。
- 前端 `${FRONTEND_SERVICE_URL}/platform` 可访问。
- Playwright 能完成登录和核心页面回归。

## 6. SQLite 迁移验收说明

本轮会把 `back-end/db.sqlite3` 中当前已验收数据迁移到 MySQL，但保留 `back-end/db.sqlite3` 文件作为验收备份。只有主人确认 MySQL 迁移后功能无问题，后续才可单独决定是否删除 SQLite 文件。

## 7. 常用排查命令

查看 Docker 服务：

```powershell
docker compose ps
```

查看 MySQL 日志：

```powershell
docker compose logs --tail=80 mysql
```

查看 Jenkins 日志：

```powershell
docker compose logs --tail=80 jenkins
```

验证后端登录接口：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$env:BACKEND_SERVICE_URL/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body (@{
    username = $env:INITIAL_ADMIN_USERNAME
    password = $env:INITIAL_ADMIN_PASSWORD
  } | ConvertTo-Json)
```

如果登录返回 400/401：

- 确认后端连接的是 Docker MySQL。
- 重新执行 `python manage.py init_admin`。
- 确认前端代理目标 `FRONTEND_DEV_API_PROXY_TARGET` 指向后端服务。

如果后端连接 MySQL 返回 `Access denied for user 'root'`：

- 当前 `.env` 密码可能和旧数据卷的真实 root 密码不一致。
- `.env` 只影响首次初始化或后续启动环境，不会修改已有数据卷内的 MySQL root 密码。
- 默认 root 连接需要使用旧数据卷真实密码设置 `MYSQL_ROOT_PASSWORD`；只有使用非 root 用户时才设置 `MYSQL_PASSWORD`，或在确认可丢弃数据后重建数据卷。

## 8. 停止服务

停止前后端开发进程：

```powershell
Ctrl+C
```

停止 Docker 服务但保留数据：

```powershell
docker compose down
```

不要执行 `docker compose down -v`，除非已经确认可以删除本地 MySQL 和 Jenkins 数据卷。
