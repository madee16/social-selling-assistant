param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function ColorWrite($color, $msg) {
    Write-Host $msg -ForegroundColor $color
}

ColorWrite Cyan "========================================"
ColorWrite Cyan "  Social Selling Assistant - Quick Start"
ColorWrite Cyan "========================================"
Write-Host ""

# --- Check Python ---
try {
    $pyVer = python --version 2>&1
    ColorWrite Green "  Python: $pyVer"
} catch {
    ColorWrite Red "  Python not found! Install from https://www.python.org/downloads/"
    exit 1
}

# --- Check Node ---
try {
    $nodeVer = node --version 2>&1
    ColorWrite Green "  Node: $nodeVer"
} catch {
    ColorWrite Red "  Node not found! Install from https://nodejs.org/"
    exit 1
}

Write-Host ""

# --- Backend setup ---
ColorWrite Yellow "[1/4] Installing backend dependencies..."
Set-Location "$root\backend"
if ($Install) {
    python -m venv venv
}
if (Test-Path "venv") {
    $pip = "$root\backend\venv\Scripts\pip"
    $uvicorn = "$root\backend\venv\Scripts\uvicorn"
} else {
    $pip = "pip"
    $uvicorn = "uvicorn"
}
& $pip install -r requirements.txt --quiet
ColorWrite Green "  Done!"

# --- Frontend setup ---
ColorWrite Yellow "[2/4] Installing frontend dependencies..."
Set-Location "$root\frontend"
& npm install --silent
ColorWrite Green "  Done!"

# --- Frontend build (Vite proxy already configured) ---
ColorWrite Yellow "[3/4] Checking frontend..."

# --- Start backend ---
ColorWrite Yellow "[4/4] Starting servers..."
Write-Host ""

$backDir = "$root\backend"
$frontDir = "$root\frontend"

# Kill any existing processes on our ports
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force

# Start backend
ColorWrite Cyan "  Starting backend on http://localhost:8001 ..."
$backendJob = Start-Job -ScriptBlock {
    param($dir, $uvicornPath)
    Set-Location $dir
    if ($uvicornPath -and (Test-Path $uvicornPath)) {
        & $uvicornPath app.main:app --host 0.0.0.0 --port 8001 --reload
    } else {
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    }
} -ArgumentList $backDir, $uvicorn

Start-Sleep 3

# Start frontend
ColorWrite Cyan "  Starting frontend on http://localhost:5173 ..."
$frontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npx vite --host
} -ArgumentList $frontDir

Start-Sleep 3

# Check if they started
$backRunning = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8001/docs" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $backRunning = $true }
} catch {}

$frontRunning = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $frontRunning = $true }
} catch {}

Write-Host ""
if ($backRunning) {
    ColorWrite Green "  ✓ Backend running at http://localhost:8001"
} else {
    ColorWrite Red "  ✗ Backend failed to start. Check logs above."
}
if ($frontRunning) {
    ColorWrite Green "  ✓ Frontend running at http://localhost:5173"
} else {
    ColorWrite Red "  ✗ Frontend failed to start. Check logs above."
}

Write-Host ""
ColorWrite Cyan "========================================"
if ($backRunning -and $frontRunning) {
    ColorWrite Green "  Open http://localhost:5173 in your browser"
    ColorWrite Green "  Demo login: demo@socialselling.tn / demo123"
} else {
    ColorWrite Red "  Some services failed to start."
    ColorWrite Red "  Start backend manually:  cd backend && python -m uvicorn app.main:app --reload --port 8001"
    ColorWrite Red "  Start frontend manually: cd frontend && npx vite"
}
ColorWrite Cyan "========================================"
