Set-Location D:\neurotwin

Write-Host "=== Fix: voice lip_sync + neo4j healthcheck ===" -ForegroundColor Cyan

# 1. Rebuild voice (lip_sync.py now exists on disk, copy it into the build context)
Write-Host "[1/3] Copying lip_sync.py into voice build context..." -ForegroundColor Yellow
Copy-Item -Force services\voice\app\lip_sync.py services\voice\services\common\.. 2>$null
# The FIX_NOW.ps1 used context=./services/voice, so lip_sync.py is already in the right place
# Just rebuild:
Write-Host "[2/3] Rebuilding voice..." -ForegroundColor Yellow
docker compose build --no-cache voice
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: voice build" -ForegroundColor Red; exit 1 }
Write-Host "  voice OK" -ForegroundColor Green

# 2. Restart neo4j with new healthcheck (no rebuild needed, just restart for new compose config)
Write-Host "[3/3] Restarting neo4j with fixed healthcheck (bash TCP)..." -ForegroundColor Yellow
docker compose stop neo4j 2>$null
docker compose rm -f neo4j 2>$null
docker compose up -d neo4j

Write-Host "Waiting 130s for neo4j JVM..." -ForegroundColor Gray
Start-Sleep 130

$health = docker inspect neurotwin-neo4j --format "{{.State.Health.Status}}" 2>&1
Write-Host "neo4j health: $health" -ForegroundColor $(if ($health -eq 'healthy') {'Green'} else {'Red'})

# 3. Restart voice with the rebuilt image
Write-Host "Restarting voice container..." -ForegroundColor Yellow
docker compose stop voice 2>$null
docker compose up -d voice

# 4. Start neo4j-dependent services if neo4j healthy
if ($health -eq 'healthy') {
    Write-Host "Starting neo4j-dependent services..." -ForegroundColor Yellow
    docker compose up -d agents codereview visual-identity
}

Start-Sleep 20

Write-Host ""
Write-Host "=== FINAL STATUS ===" -ForegroundColor Cyan
docker ps --format "table {{.Names}}`t{{.Status}}"
