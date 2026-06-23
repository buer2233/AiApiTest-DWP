$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

docker compose version | Out-Null

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Review MYSQL_ROOT_PASSWORD before shared use."
}

docker compose up -d mysql jenkins
docker compose ps

Write-Host ""
Write-Host "Jenkins: http://localhost:$((Get-Content .env | Select-String '^JENKINS_HTTP_PORT=' | ForEach-Object { $_.ToString().Split('=')[1] }) -replace '^$','8080')"
Write-Host "MySQL: 127.0.0.1:$((Get-Content .env | Select-String '^MYSQL_HOST_PORT=' | ForEach-Object { $_.ToString().Split('=')[1] }) -replace '^$','3307')"
Write-Host "Initial Jenkins password:"
Write-Host "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
