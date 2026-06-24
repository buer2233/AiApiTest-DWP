# 当前项目所有服务快速启动说明

## 目标

本文档用于在本机快速启动当前 CICD AI 自动化测试平台的全部开发服务，并完成一次浏览器登录验收。

启动范围：

- Docker MySQL：后端 DRF 使用的本地数据库。
- Docker Jenkins：本地 Jenkins 服务，用于后续 Pipeline 配置和任务触发。
- DRF 后端：提供登录、测试任务、失败用例、Jenkins 查询和 Allure 报告入口 API。
- Vue 3 前端：测试平台界面。
- Playwright 浏览器验证：登录进入测试平台首页。

本文档不记录真实密码、token、Jenkins API Token 或生产地址。本地 `.env` 属于私有配置，不提交 git。

## 前置条件

在项目根目录执行命令：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP
```

确认以下工具可用：

```powershell
docker compose version
python --version
node --version
npm --version
```

如果首次运行前端浏览器验证，需要 Playwright 或本地浏览器环境可用。当前 Codex 环境可直接使用 Playwright MCP 进行验收。

## 端口约定

| 服务 | 地址 |
|------|------|
| MySQL | `127.0.0.1:3307` |
| Jenkins | `http://localhost:8080` |
| DRF 后端 | `http://127.0.0.1:8000` |
| Vue 前端 | `http://127.0.0.1:5173` |

如果端口被占用，优先修改 `.env` 中的 Docker 端口；前后端开发端口可在启动命令中调整。

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
```

查看 Jenkins 首次初始化密码：

```powershell
docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

该密码只用于本地 Jenkins 首次初始化，不要写入项目文档或提交。

## 2. 准备后端环境变量

Docker Compose 默认 MySQL root 密码来自本地 `.env`。后端必须使用同一个密码连接数据库。

PowerShell 示例：

```powershell
$env:MYSQL_DATABASE="ai_api_test_platform"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="<填写本机 .env 中 MYSQL_ROOT_PASSWORD 的值>"
$env:MYSQL_PORT="3307"
$env:ALLURE_REPORTS_ROOT="D:\AI\Hermes\dev\AiApiTest-DWP\api-test\runtime\ci-runs"
```

注意：

- 不要把真实 `$env:MYSQL_PASSWORD` 写入仓库文件。
- 如果 `.env` 中 `MYSQL_HOST_PORT` 改成了其他端口，`MYSQL_PORT` 也要同步调整。
- 如果复用旧的 `aiapitest-mysql-data` 数据卷，MySQL root 密码以数据卷初始化时的真实状态为准，不会因为重新生成 `.env` 自动变更。出现 `Access denied for user 'root'` 时，先用本地私有方式确认旧数据卷密码，再设置 `$env:MYSQL_PASSWORD`。

## 3. 启动 DRF 后端

安装依赖：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\back-end
python -m pip install -r requirements.txt
```

执行数据库迁移：

```powershell
python manage.py migrate
```

创建本地演示管理员账号。该账号只用于本机快速验收：

```powershell
@'
from apps.accounts.models import User

username = "admin"
password = "admin123456"
user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
)
if created:
    user.set_password(password)
else:
    user.role = User.Role.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
user.save()
print("local demo admin ready")
'@ | python manage.py shell
```

启动后端：

```powershell
python manage.py runserver 127.0.0.1:8000
```

后端接口文档地址：

```text
http://127.0.0.1:8000/api/docs/
```

## 4. 启动 Vue 3 前端

另开一个 PowerShell 窗口：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

访问平台：

```text
http://127.0.0.1:5173/platform
```

前端开发服务会把 `/api` 请求代理到：

```text
http://127.0.0.1:8000
```

## 5. 登录验收

浏览器打开：

```text
http://127.0.0.1:5173/platform
```

未登录时应自动跳转到：

```text
http://127.0.0.1:5173/login?redirect=/platform
```

输入本地演示账号：

```text
用户名：admin
密码：admin123456
```

登录成功后应进入测试平台，并看到模块通过率、失败用例、Jenkins 入口和 Allure 报告入口相关界面。

## 6. Playwright 验证步骤

使用 Playwright 验证时，按以下检查点执行：

1. 打开 `http://127.0.0.1:5173/platform`。
2. 确认自动跳转到登录页。
3. 输入 `admin` / `admin123456`。
4. 点击登录按钮。
5. 确认 URL 回到 `/platform`。
6. 确认页面存在测试平台主界面内容。

验收通过标准：

- Jenkins 容器处于 running 或 healthy 状态。
- MySQL 容器处于 healthy 状态。
- 后端 `http://127.0.0.1:8000/api/docs/` 可访问。
- 前端 `http://127.0.0.1:5173/platform` 可访问。
- Playwright 能完成登录并进入平台。

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
  -Uri http://127.0.0.1:8000/api/auth/login/ `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123456"}'
```

如果登录返回 400：

- 确认后端连接的是 Docker MySQL `127.0.0.1:3307`。
- 重新执行本地演示管理员创建命令。
- 确认前端代理目标仍是 `http://127.0.0.1:8000`。

如果后端连接 MySQL 返回 `Access denied for user 'root'`：

- 当前 `.env` 密码可能和旧数据卷的真实 root 密码不一致。
- `.env` 只影响首次初始化或后续启动环境，不会修改已有数据卷内的 MySQL root 密码。
- 需要使用旧数据卷真实密码设置 `$env:MYSQL_PASSWORD`，或在确认可丢弃数据后重建数据卷。

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
