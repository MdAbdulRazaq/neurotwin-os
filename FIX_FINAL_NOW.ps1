#!/usr/bin/env pwsh

Write-Host @"
============================================
 NEUROTWIN — Final Fixes (lip_sync + neo4j)
============================================
"@ -ForegroundColor Cyan

# Rebuild voice with lip_sync.py now present
Write-Host "[1/3] Rebuilding voice..." -ForegroundColor Yellow
docker compose build --no-cache voice 2>&1 | Select-Object -Last 3

if ($LASTEXITCODE -ne 0) {
    Write-Host "  FAILED: voice" -ForegroundColor Red
    exit 1
}
Write-Host "  voice OK" -ForegroundColor Green

# Restart neo4j with netcat healthcheck (more reliable than bash TCP)
Write-Host "[2/3] Restarting neo4j with fixed healthcheck..." -ForegroundColor Yellow
docker compose down --remove-orphans 2>&1 | Select-Object -Last 1
docker compose up -d postgres redis neo4j 2>&1 | Select-Object -Last 1

# Wait for neo4j to pass healthcheck (up to 180s)
Write-Host "[3/3] Waiting for neo4j to become healthy (max 180s)..." -ForegroundColor Yellow
$neo4j_healthy = $false
for ($i = 1; $i -le 18; $i++) {
    Start-Sleep 10
    $status = docker inspect neurotwin-neo4j --format='{{.State.Health.Status}}' 2>&1
    Write-Host "  [$i/18] $status" -ForegroundColor Gray
    if ($status -eq "healthy") {
        $neo4j_healthy = $true
        break
    }
}

if (-not $neo4j_healthy) {
    Write-Host "neo4j still unhealthy after 180s. Checking logs..." -ForegroundColor Yellow
    docker logs neurotwin-neo4j --tail 5
    exit 1
}

# Start all other services
Write-Host "neo4j is healthy! Starting remaining services..." -ForegroundColor Green
docker compose up -d 2>&1 | Select-Object -Last 2

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " WAITING 60s FOR ALL SERVICES TO STABILIZE"
Write-Host "============================================" -ForegroundColor Green
Start-Sleep 60

# Final status
docker ps --format "table {{.Names}}\t{{.Status}}"
