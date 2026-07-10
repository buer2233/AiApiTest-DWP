# Docker quick deployment script for Windows PowerShell.
# This script starts MySQL and Jenkins from the repository root.
# It does not start backend, frontend, or api-test application processes.
$ErrorActionPreference = "Stop"

# The script lives in scripts/, so its parent directory is the repository root.
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Docker CLI is required for compose operations.
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH."
}

# Validate Docker Compose v2 before service startup.
docker compose version | Out-Null

# .env is local and private; create it from the template on first run.
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Fill private secrets in .env before starting shared services."
}

function Set-PrivateEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $line = "$Key=$Value"
    $escapedKey = [regex]::Escape($Key)
    $updated = $false
    $newLines = @()

    if (Test-Path -LiteralPath $Path) {
        foreach ($existingLine in Get-Content -LiteralPath $Path) {
            if ($existingLine -match "^\s*$escapedKey=") {
                $newLines += $line
                $updated = $true
            } else {
                $newLines += $existingLine
            }
        }
    }

    if (-not $updated) {
        $newLines += $line
    }
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($Path, [string[]]$newLines, $utf8WithoutBom)
}

# Start only shared MySQL and Jenkins services, preserving existing volumes.
docker compose up -d mysql jenkins
docker compose ps

# Local Jenkins init script writes a runtime API token; store it in private .env.
$jenkinsApiCredential = ""
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $jenkinsApiCredential = (docker exec aiapitest-jenkins sh -lc "cat /var/jenkins_home/aiapitest-local-api-token.txt 2>/dev/null || true").Trim()
    if ($jenkinsApiCredential -match "^[^:]+:.+") {
        break
    }
    Start-Sleep -Seconds 1
}
if ($jenkinsApiCredential -match "^[^:]+:.+") {
    $parts = $jenkinsApiCredential.Split(":", 2)
    Set-PrivateEnvValue -Path ".env" -Key "JENKINS_USERNAME" -Value $parts[0]
    Set-PrivateEnvValue -Path ".env" -Key "JENKINS_API_TOKEN" -Value $parts[1]
    Write-Host "Injected local Jenkins API credentials into private .env. Restart the backend to reload them."
} else {
    Write-Warning "Local Jenkins API token was not ready. Re-run this script after Jenkins finishes startup."
}

# Read ports from .env and fall back to Compose defaults when missing.
$envLines = Get-Content .env
$jenkinsPublicBaseUrl = ($envLines | Select-String '^JENKINS_PUBLIC_BASE_URL=' | ForEach-Object { $_.ToString().Split('=', 2)[1] }) -replace '^$','http://localhost:8080'
$mysqlBindHost = ($envLines | Select-String '^MYSQL_BIND_HOST=' | ForEach-Object { $_.ToString().Split('=', 2)[1] }) -replace '^$','127.0.0.1'
$mysqlHostPort = ($envLines | Select-String '^MYSQL_HOST_PORT=' | ForEach-Object { $_.ToString().Split('=', 2)[1] }) -replace '^$','3307'
Write-Host ""
Write-Host "Jenkins: $jenkinsPublicBaseUrl"
Write-Host "MySQL: ${mysqlBindHost}:${mysqlHostPort}"
Write-Host "Initial Jenkins password:"
Write-Host "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
