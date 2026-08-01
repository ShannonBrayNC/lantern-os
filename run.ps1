$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host "Lantern OS local startup" -ForegroundColor Cyan

$branch = git branch --show-current 2>$null
$commit = git rev-parse --short HEAD 2>$null
Write-Host "Branch: $branch"
Write-Host "Commit: $commit"

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    $processName = if ($process) { $process.ProcessName } else { 'unknown' }
    throw "Port 8000 is already in use by PID $($listener.OwningProcess) ($processName). Stop the previous Lantern OS/Uvicorn process first, or run: Stop-Process -Id $($listener.OwningProcess) -Force"
}

if (-not (Test-Path .venv)) {
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Validating imported application..." -ForegroundColor Cyan
python -c "from app.main import app; print(f'Loaded {app.title} {app.version}')"

Write-Host "Starting Lantern OS at http://localhost:8000" -ForegroundColor Green
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
