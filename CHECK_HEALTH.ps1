# NEUROTWIN OS - Health Check Script
# Verifies all services are running and healthy

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - HEALTH CHECK" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "[1/3] Docker Status:" -ForegroundColor Yellow
$dockerStatus = docker ps 2>&1
if ($dockerStatus -like "*failed to connect*") {
    Write-Host "ERROR: Docker daemon is NOT running" -ForegroundColor Red
    exit 1
} else {
    Write-Host "OK: Docker daemon is running" -ForegroundColor Green
}
Write-Host ""

# Check containers
Write-Host "[2/3] Container Status:" -ForegroundColor Yellow
$containers = docker ps --format "table {{.Names}}\t{{.Status}}"
Write-Host $containers
Write-Host ""

# Check services
Write-Host "[3/3] Service Health:" -ForegroundColor Yellow

$services = @(
    @{name="API"; url="http://localhost:8000/health"; port=8000},
    @{name="Web"; url="http://localhost:3000"; port=3000},
    @{name="Nginx"; url="http://localhost"; port=80},
    @{name="Perception"; url="http://localhost:8001"; port=8001},
    @{name="Memory"; url="http://localhost:8002"; port=8002},
    @{name="Avatar"; url="http://localhost:8003"; port=8003}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest $service.url -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 404) {
            Write-Host "OK: $($service.name) responding (port $($service.port))" -ForegroundColor Green
        }
    } catch {
        Write-Host "ERROR: $($service.name) not responding (port $($service.port))" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Open http://localhost in your browser" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
