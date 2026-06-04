# FIX_REMAINING.ps1 — Fix voice + neo4j + web
# Run from D:\neurotwin: powershell -ExecutionPolicy Bypass -File FIX_REMAINING.ps1

Set-Location D:\neurotwin
$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " NEUROTWIN — Fixing remaining 3 issues" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── Fix 1: Rebuild voice with corrected phonemizer version ───────────────────
Write-Host "`n[1/4] Rebuilding voice (phonemizer version fixed)..." -ForegroundColor Yellow
docker compose build --no-cache voice
if ($LASTEXITCODE -eq 0) {
    Write-Host "  voice build OK" -ForegroundColor Green
} else {
    Write-Host "  voice build FAILED" -ForegroundColor Red
}

# ── Fix 2: Restart neo4j with new healthcheck (no -f flag, longer timeout) ───
Write-Host "`n[2/4] Restarting neo4j with fixed healthcheck..." -ForegroundColor Yellow
docker compose stop neo4j
docker compose rm -f neo4j
docker compose up -d neo4j
Write-Host "  neo4j restarted. Waiting 120s for JVM..." -ForegroundColor Gray
Start-Sleep -Seconds 120

# Check neo4j status
$neo4jStatus = docker inspect --format "{{.State.Health.Status}}" neurotwin-neo4j 2>$null
Write-Host "  neo4j health: $neo4jStatus" -ForegroundColor $(if ($neo4jStatus -eq "healthy") { "Green" } else { "Yellow" })

# ── Fix 3: Start neo4j-dependent services if neo4j is now healthy ─────────────
Write-Host "`n[3/4] Starting neo4j-dependent services..." -ForegroundColor Yellow
docker compose up -d codereview visual-identity agents
Start-Sleep -Seconds 15

# ── Fix 4: Start voice and web ─────────────────────────────────────────────────
Write-Host "`n[4/4] Starting voice and web..." -ForegroundColor Yellow
docker compose up -d voice web
Start-Sleep -Seconds 30

# ── Final status ──────────────────────────────────────────────────────────────
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " FINAL STATUS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
docker ps --format "table {{.Names}}`t{{.Status}}"

Write-Host "`n--- Neo4j logs (last 10 lines) ---" -ForegroundColor Yellow
docker logs neurotwin-neo4j --tail 10 2>&1

Write-Host "`n--- Voice logs (last 10 lines) ---" -ForegroundColor Yellow
docker logs neurotwin-voice --tail 10 2>&1

Write-Host "`nDone." -ForegroundColor Cyan
