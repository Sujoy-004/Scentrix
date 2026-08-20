# start.ps1
# One-command dev launcher for Scentrix.
# On first run it creates the backend venv, installs requirements and
# frontend deps; afterwards it just starts both servers in two windows.
# Usage: .\start.ps1  (run from the repo root)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv = Join-Path $backend "venv"
$py = Join-Path $venv "Scripts\python.exe"

# --- Backend setup ----------------------------------------------------------
if (-not (Test-Path $py)) {
    Write-Host "Creating backend venv..."
    python -m venv $venv
}

Write-Host "Checking backend dependencies..."
& $py -m pip install -q -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed (backend deps)." }

# --- Frontend setup ---------------------------------------------------------
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies (npm install)..."
    Push-Location $frontend
    try { npm install }
    finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
}

# --- Port cleanup ----------------------------------------------------------
# Next.js auto-bumps to 3001 if 3000 is held by a stale dev server; uvicorn
# similarly conflicts on 8000. Free both ports before launching so the
# frontend is always http://localhost:3000.
function Free-Port([int]$Port) {
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($conn in $listeners) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -in @("node", "python")) {
            Write-Host "  port $Port in use by $($proc.ProcessName) (PID $($proc.Id)) - stopping..."
            Stop-Process -Id $proc.Id -Force
        }
    }
}

Write-Host "Checking ports..."
Free-Port 3000
Free-Port 8000

# --- Launch ----------------------------------------------------------------
Write-Host ""
Write-Host "Starting Scentrix backend  -> http://localhost:8000/docs"
Start-Process pwsh -ArgumentList "-NoExit", "-NoProfile", "-c", "Set-Location '$backend'; & '$py' -m uvicorn app.main:app --reload"

Write-Host "Starting Scentrix frontend -> http://localhost:3000"
Start-Process pwsh -ArgumentList "-NoExit", "-NoProfile", "-c", "Set-Location '$frontend'; npm run dev -- -p 3000"

Write-Host "Done. Ctrl+C in each window stops that server."