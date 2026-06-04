# FIX_FINAL.ps1 — Fix voice (lip_sync.py) + neo4j (healthcheck)
# Run: powershell -ExecutionPolicy Bypass -File FIX_FINAL.ps1

Set-Location D:\neurotwin
$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " NEUROTWIN — Final 2-service fix" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── Fix 1: Rebuild voice (lip_sync.py now exists) ────────────────────────────
Write-Host "`n[1/3] Rebuilding voice with lip_sync.py..." -ForegroundColor Yellow
docker compose build --no-cache voice
if ($LASTEXITCODE -eq 0) {
    Write-Host "  voice OK" -ForegroundColor Green
} else {
    Write-Host "  voice FAILED" -ForegroundColor Red
}

# ── Fix 2: Restart neo4j with bash TCP healthcheck ────────────────────────────
Write-Host "`n[2/3] Restarting neo4j with bash TCP healthcheck (no curl needed)..." -ForegroundColor Yellow
docker compose stop neo4j
docker compose rm -f neo4j
docker compose up -d neo4j
Write-Host "  Waiting 90s for neo4j JVM..." -ForegroundColor Gray
Start-Sleep -Seconds 90

$neo4jStatus = docker inspect --format "{{.State.Health.Status}}" neurotwin-neo4j 2>$null
Write-Host "  neo4j: $neo4jStatus" -ForegroundColor $(if ($neo4jStatus -eq "healthy") { "Green" } else { "Yellow" })

# ── Fix 3: Start everything that was waiting on neo4j + voice ─────────────────
Write-Host "`n[3/3] Starting all dependent services..." -ForegroundColor Yellow
docker compose up -d --remove-orphans
Start-Sleep -Seconds 20

# ── Final status ───────────────────────────────────────────────────────────────
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " FINAL STATUS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
docker ps --format "table {{.Names}}`t{{.Status}}"

Write-Host "`n--- voice logs (last 5) ---" -ForegroundColor Yellow
docker logs neurotwin-voice --tail 5 2>&1

Write-Host "`n--- neo4j health ---" -ForegroundColor Yellow
docker inspect --format "{{.State.Health.Status}} | last check: {{(index .State.Health.Log 0).Output}}" neurotwin-neo4j 2>&1
