[CmdletBinding()]
param(
    [ValidateSet('true', 'false')]
    [string]$BuildAll = 'true',

    [ValidateSet('true', 'false')]
    [string]$RunFullTests = 'false'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$coreScript = Join-Path $repoRoot 'jenkins/scripts/platform_bootstrap_cli.py'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCommand) {
    Write-Error 'Python was not found on PATH. Install Python, then rerun this trigger command.'
    exit 1
}

Push-Location $repoRoot
try {
    & $pythonCommand.Source $coreScript trigger --build-all $BuildAll --run-full-tests $RunFullTests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
