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
    Write-Warning "Created .env from .env.example. Add the private configuration documented in docker/DEPLOYMENT.md, then rerun this script."
    exit 2
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

function ConvertFrom-DotEnvValue {
    param([Parameter(Mandatory = $true)][string]$RawValue)

    $value = $RawValue.Trim()
    $quote = [char]0
    for ($index = 0; $index -lt $value.Length; $index++) {
        $character = $value[$index]
        if ($character -eq [char]34 -or $character -eq [char]39) {
            if ($quote -eq [char]0) {
                $quote = $character
            } elseif ($quote -eq $character) {
                $quote = [char]0
            }
            continue
        }
        if ($character -eq '#' -and $quote -eq [char]0 -and ($index -eq 0 -or [char]::IsWhiteSpace($value[$index - 1]))) {
            $value = $value.Substring(0, $index).TrimEnd()
            break
        }
    }
    if ($value.Length -ge 2 -and (($value[0] -eq [char]34 -and $value[-1] -eq [char]34) -or ($value[0] -eq [char]39 -and $value[-1] -eq [char]39))) {
        return $value.Substring(1, $value.Length - 2)
    }
    return $value
}

function Format-HostPortHost {
    param([Parameter(Mandatory = $true)][string]$HostName)

    $normalized = $HostName.Trim()
    if ($normalized.StartsWith('[') -and $normalized.EndsWith(']')) {
        $normalized = $normalized.Substring(1, $normalized.Length - 2)
    }
    return $(if ($normalized.Contains(':')) { "[$normalized]" } else { $normalized })
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

# 地址提示与应用相同，都从平台公开主机、协议和服务端口派生。
$envValues = @{}
$addressKeys = @('PLATFORM_PUBLIC_HOST', 'PLATFORM_PUBLIC_SCHEME', 'JENKINS_HTTP_PORT', 'MYSQL_HOST_PORT')
Get-Content -LiteralPath ".env" | ForEach-Object {
    if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and $Matches[1] -in $addressKeys) {
        $envValues[$Matches[1]] = ConvertFrom-DotEnvValue -RawValue $Matches[2]
    }
}
$platformPublicHost = if ($envValues['PLATFORM_PUBLIC_HOST']) { $envValues['PLATFORM_PUBLIC_HOST'] } else { '127.0.0.1' }
$platformPublicScheme = if ($envValues['PLATFORM_PUBLIC_SCHEME']) { $envValues['PLATFORM_PUBLIC_SCHEME'] } else { 'http' }
$jenkinsHttpPort = if ($envValues['JENKINS_HTTP_PORT']) { $envValues['JENKINS_HTTP_PORT'] } else { '8080' }
$mysqlHostPort = if ($envValues['MYSQL_HOST_PORT']) { $envValues['MYSQL_HOST_PORT'] } else { '3307' }
$publicDisplayHost = Format-HostPortHost -HostName $platformPublicHost
Write-Host ""
Write-Host "Jenkins: ${platformPublicScheme}://${publicDisplayHost}:${jenkinsHttpPort}"
Write-Host "MySQL: ${publicDisplayHost}:${mysqlHostPort}"
Write-Host "Initial Jenkins password:"
Write-Host "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
