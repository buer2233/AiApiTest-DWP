# Docker 快速部署脚本（Windows PowerShell）。
# 本脚本在仓库根目录启动 MySQL 和 Jenkins 两个基础服务，
# 不负责启动后端、前端或 api-test 应用进程。
$ErrorActionPreference = "Stop"

# 脚本位于 scripts/，因此父目录就是仓库根目录。
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Docker CLI 是后续 compose 操作的硬依赖，缺失时直接中止并给出明确错误。
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

# 提前确认 Docker Compose v2 可用，避免执行到服务启动阶段才失败。
docker compose version | Out-Null

# .env 是本地私有配置，不提交 git；首次部署时从模板复制一份。
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Review MYSQL_ROOT_PASSWORD before shared use."
}

# 只启动平台依赖的 MySQL 和 Jenkins，保留已有数据卷。
docker compose up -d mysql jenkins
docker compose ps

# 从 .env 读取端口并输出访问提示；读取不到时回退到 Compose 默认端口。
Write-Host ""
Write-Host "Jenkins: http://localhost:$((Get-Content .env | Select-String '^JENKINS_HTTP_PORT=' | ForEach-Object { $_.ToString().Split('=')[1] }) -replace '^$','8080')"
Write-Host "MySQL: 127.0.0.1:$((Get-Content .env | Select-String '^MYSQL_HOST_PORT=' | ForEach-Object { $_.ToString().Split('=')[1] }) -replace '^$','3307')"
Write-Host "Initial Jenkins password:"
Write-Host "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
