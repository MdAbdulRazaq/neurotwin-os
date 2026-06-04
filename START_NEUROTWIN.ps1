# NEUROTWIN OS - Complete Startup Script
# Restarts Docker Desktop and all microservices

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - STARTUP SEQUENCE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill existing Docker processes
Write-Host "[1/6] Terminating existing Docker processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.Name -like "*Docker*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
Write-Host "OK: Docker processes stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Start Docker Desktop
Write-Host "[2/6] Starting Docker Desktop..." -ForegroundColor Yellow
$dockerShortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\docker-desktop\Docker Desktop.lnk"
if (Test-Path $dockerShortcut) {
    & $dockerShortcut
    Write-Host "OK: Docker Desktop started" -ForegroundColor Green
}
Start-Sleep -Seconds 45
Write-Host ""

# Step 3: Verify Docker is responsive
Write-Host "[3/6] Verifying Docker is responsive..." -ForegroundColor Yellow
$maxRetries = 5
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $result = docker ps 2>&1
        if ($result -and -not ($result -like "*failed to connect*")) {
            Write-Host "OK: Docker is responsive" -ForegroundColor Green
            break
        }
    } catch {}
    $retry++
    if ($retry -lt $maxRetries) {
        Write-Host "  Retrying... ($retry/$maxRetries)" -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}
if ($retry -eq $maxRetries) {
    Write-Host "ERROR: Docker failed to respond" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Start all containers
Write-Host "[4/6] Starting all NEUROTWIN services..." -ForegroundColor Yellow
cd D:\neurotwin
docker-compose up -d
Write-Host "OK: All containers started" -ForegroundColor Green
Write-Host ""

# Step 5: Wait for containers to initialize
Write-Host "[5/6] Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "OK: Services initialized" -ForegroundColor Green
Write-Host ""

# Step 6: Verify all containers are running
Write-Host "[6/6] Verifying all containers are running..." -ForegroundColor Yellow
$containers = docker ps --format "table {{.Names}}\t{{.Status}}"
Write-Host $containers
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - STARTUP COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access your applications:" -ForegroundColor Green
Write-Host "  Web Dashboard:    http://localhost" -ForegroundColor White
Write-Host "  Web (Direct):     http://localhost:3000" -ForegroundColor White
Write-Host "  API:              http://localhost:8000" -ForegroundColor White
Write-Host "  Perception:       http://localhost:8001" -ForegroundColor White
Write-Host "  Memory:           http://localhost:8002" -ForegroundColor White
Write-Host "  Avatar:           http://localhost:8003" -ForegroundColor White
Write-Host "  Grafana Monitor:  http://localhost:3001" -ForegroundColor White
Write-Host "  Prometheus:       http://localhost:9090" -ForegroundColor White
Write-Host ""
