# Launch DApp dashboard: FastAPI backend + Vite frontend
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path "$PSScriptRoot\..").Path }
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Backend = Join-Path $PSScriptRoot "backend"
$Frontend = Join-Path $PSScriptRoot "frontend"
$ApiPort = 8000
$UiPort = 5173

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

function Stop-Tree([int]$ProcessId) {
    # npm.cmd and uvicorn --reload spawn children; kill the whole tree so nothing keeps the port
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
}

# Free ports held by a previous dashboard run (only our own uvicorn / vite processes)
foreach ($port in @($ApiPort, $UiPort)) {
    $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $owners) {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -match "uvicorn|vite") {
            Write-Host "Stopping leftover dashboard process $procId on port $port" -ForegroundColor Yellow
            Stop-Tree $procId
        } else {
            Write-Error "Port $port is in use by another program (PID $procId): $cmd"
        }
    }
}
Start-Sleep -Milliseconds 500

Write-Host "Starting API on http://127.0.0.1:$ApiPort ..." -ForegroundColor Cyan
$api = Start-Process -FilePath $VenvPython -ArgumentList @(
    "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "$ApiPort", "--reload"
) -WorkingDirectory $Backend -PassThru -NoNewWindow

Start-Sleep -Seconds 2
if ($api.HasExited) {
    Write-Error "API exited during startup (exit code $($api.ExitCode)). See the error above."
}

Write-Host "Starting UI on http://127.0.0.1:$UiPort ..." -ForegroundColor Cyan
$ui = Start-Process -FilePath $NpmPath -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$UiPort", "--strictPort") `
    -WorkingDirectory $Frontend -PassThru -NoNewWindow

Write-Host ""
Write-Host "Dashboard ready:" -ForegroundColor Green
Write-Host "  UI:  http://127.0.0.1:$UiPort"
Write-Host "  API: http://127.0.0.1:$ApiPort/api/meta"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

try {
    while (-not $api.HasExited -and -not $ui.HasExited) {
        Start-Sleep -Seconds 1
    }
    if ($api.HasExited) { Write-Host "API process exited (code $($api.ExitCode))." -ForegroundColor Red }
    if ($ui.HasExited) { Write-Host "UI process exited (code $($ui.ExitCode))." -ForegroundColor Red }
} finally {
    foreach ($p in @($api, $ui)) {
        if ($p -and -not $p.HasExited) { Stop-Tree $p.Id }
    }
}
