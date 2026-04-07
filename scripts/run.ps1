param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvActivate = Join-Path $RepoRoot ".venv\\Scripts\\Activate.ps1"

if (Test-Path $VenvActivate) {
    . $VenvActivate
}

$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host "Starting LOT MVP on http://$HostAddress`:$Port"
Write-Host "Repo root: $RepoRoot"

Set-Location $RepoRoot

python -m uvicorn lot.main:app --reload --host $HostAddress --port $Port
