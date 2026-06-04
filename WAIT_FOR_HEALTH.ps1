# NEUROTWIN OS - Wait for Health Script
# Continuously checks until all services are healthy

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - WAITING FOR HEALTH" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$maxWaitSeconds = 120
$checkInterval = 5
$elapsed = 0

while ($elapsed -lt $maxWaitSeconds) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Checking services..." -ForegroundColor Gray
    
    $allHealthy = $true
    
    # Test API
    try {
        $api = Invoke-WebRequest http://localhost:8000/health -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($api.StatusCode -eq 200) {
            Write-Host "  API: OK (200)" -ForegroundColor Green
        } else {
            Write-Host "  API: $($api.StatusCode)" -ForegroundColor Yellow
            $allHealthy = $false
        }
    } catch {
        Write-Host "  API: STARTING..." -ForegroundColor Yellow
        $allHealthy = $false
    }
    
    # Test Web
    try {
        $web = Invoke-WebRequest http://localhost:3000/api/health -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($web.StatusCode -eq 200) {
            Write-Host "  Web: OK (200)" -ForegroundColor Green
        } else {
            Write-Host "  Web: $($web.StatusCode)" -ForegroundColor Yellow
            $allHealthy = $false
        }
    } catch {
        Write-Host "  Web: STARTING..." -ForegroundColor Yellow
        $allHealthy = $false
    }
    
    # Test Nginx
    try {
        $nginx = Invoke-WebRequest http://localhost -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($nginx.StatusCode -eq 200 -or $nginx.StatusCode -eq 404) {
            Write-Host "  Nginx: OK" -ForegroundColor Green
        } else {
            Write-Host "  Nginx: $($nginx.StatusCode)" -ForegroundColor Yellow
            $allHealthy = $false
        }
    } catch {
        Write-Host "  Nginx: STARTING..." -ForegroundColor Yellow
        $allHealthy = $false
    }
    
    if ($allHealthy) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "ALL SERVICES HEALTHY!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Access NEUROTWIN:" -ForegroundColor Green
        Write-Host "  http://localhost" -ForegroundColor White
        Write-Host ""
        exit 0
    }
    
    Write-Host ""
    $elapsed += $checkInterval
    
    if ($elapsed -lt $maxWaitSeconds) {
        Write-Host "Waiting $checkInterval seconds... ($elapsed/$maxWaitSeconds)" -ForegroundColor Gray
        Start-Sleep -Seconds $checkInterval
    }
}

Write-Host "========================================" -ForegroundColor Red
Write-Host "TIMEOUT: Services did not become healthy" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "Run these to check logs:" -ForegroundColor Yellow
Write-Host "  docker logs neurotwin-api -f" -ForegroundColor White
Write-Host "  docker logs neurotwin-web -f" -ForegroundColor White
Write-Host ""
