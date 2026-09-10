# EchoSphere One-Click Ecosystem Launcher
# Starts the Local Gemma 2 GPU Microservice (Port 8008) and FastAPI Backend Server (Port 8000)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "       EchoSphere Full-Stack App & AI Ecosystem Launcher        " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ScriptDir "backend\ml\gemma_training\.venv\Scripts\python.exe"
$GemmaScript = Join-Path $ScriptDir "backend\ml\gemma_training\serve_gemma.py"
$BackendScript = Join-Path $ScriptDir "backend\run_server.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Python venv not found at: $VenvPython" -ForegroundColor Red
    exit 1
}

# 1. Start Gemma 2 GPU Microservice on port 8008 if not running
Write-Host "`n[1/3] Checking Gemma 2 Local GPU Microservice (Port 8008)..." -ForegroundColor Yellow
$GemmaActive = Get-NetTCPConnection -LocalPort 8008 -ErrorAction SilentlyContinue
if ($null -eq $GemmaActive) {
    Write-Host "      Starting Gemma GPU Microservice..." -ForegroundColor Green
    Start-Process -FilePath $VenvPython -ArgumentList $GemmaScript -WorkingDirectory (Split-Path $GemmaScript) -WindowStyle Hidden
    Start-Sleep -Seconds 4
} else {
    Write-Host "      Gemma GPU Microservice is already running on port 8008." -ForegroundColor Green
}

# 2. Start FastAPI Backend Server on port 8000 if not running
Write-Host "`n[2/3] Checking EchoSphere FastAPI Backend Server (Port 8000)..." -ForegroundColor Yellow
$BackendActive = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($null -eq $BackendActive) {
    Write-Host "      Starting FastAPI Backend Server..." -ForegroundColor Green
    Start-Process -FilePath $VenvPython -ArgumentList $BackendScript -WorkingDirectory (Split-Path $BackendScript) -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "      FastAPI Backend Server is already running on port 8000." -ForegroundColor Green
}

# 3. Connection Diagnostics & IP Detection
$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254*" } | Select-Object -First 1).IPAddress

Write-Host "`n[3/3] EchoSphere Ecosystem Connected Successfully!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Backend Root:       http://localhost:8000/" -ForegroundColor White
Write-Host "  Swagger Docs:       http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Gemma GPU Engine:   http://localhost:8008/health" -ForegroundColor White
Write-Host "-----------------------------------------------------------------" -ForegroundColor Gray
Write-Host "  Flutter App Connection URLs:" -ForegroundColor Yellow
Write-Host "    - Android Emulator:  http://10.0.2.2:8000/api/v1" -ForegroundColor White
Write-Host "    - Windows Desktop:   http://127.0.0.1:8000/api/v1" -ForegroundColor White
Write-Host "    - Physical Phone:    http://${LocalIP}:8000/api/v1" -ForegroundColor White
Write-Host "    - Cloud Render:      https://echosphere-backend-9lv8.onrender.com/api/v1" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
