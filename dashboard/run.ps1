# Launch DApp dashboard: FastAPI backend + Vite frontend
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path "$PSScriptRoot\..").Path }
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Backend = Join-Path $PSScriptRoot "backend"
$Frontend = Join-Path $PSScriptRoot "frontend"

# Ensure node is on PATH (post-winget install)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Test-Path $VenvPython)) {
    Write-Error "Missing venv at $VenvPython - create .venv and pip install -r dashboard\backend\requirements.txt"
}

# Resolve npm.cmd (Start-Process cannot launch the extensionless npm shim on Windows)
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $npm) {
    Write-Error "npm not found on PATH. Install Node.js LTS (winget install OpenJS.NodeJS.LTS) and reopen the terminal."
}
$NpmPath = $npm.Source

Write-Host "Starting API on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$api = Start-Process -FilePath $VenvPython -ArgumentList @(
    "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"
) -WorkingDirectory $Backend -PassThru -NoNewWindow

Start-Sleep -Seconds 2

Write-Host "Starting UI on http://127.0.0.1:5173 ..." -ForegroundColor Cyan
$ui = Start-Process -FilePath $NpmPath -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
    -WorkingDirectory $Frontend -PassThru -NoNewWindow

Write-Host ""
Write-Host "Dashboard ready:" -ForegroundColor Green
Write-Host "  UI:  http://127.0.0.1:5173"
Write-Host "  API: http://127.0.0.1:8000/api/meta"
Write-Host "Press Ctrl+C to stop (then close leftover processes if needed)."
Write-Host ""

try {
    Wait-Process -Id $api.Id, $ui.Id
} finally {
    foreach ($p in @($api, $ui)) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
