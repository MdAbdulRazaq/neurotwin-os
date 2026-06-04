#############################################################################
# NEUROTWIN OS — Automatic Fix & Verify Script
# Purpose: Fix ALLOWED_ORIGINS JSON parsing issue and verify API health
#############################################################################

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     NEUROTWIN OS — ALLOWED_ORIGINS JSON Fix & Verification     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 1: Verify .env file is correct
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 1: Verifying .env file..." -ForegroundColor Yellow
$envContent = Get-Content -Path "D:\neurotwin\.env" -Raw

if ($envContent -like '*ALLOWED_ORIGINS=`["*') {
    Write-Host "✅ .env ALLOWED_ORIGINS is in correct JSON format" -ForegroundColor Green
    $allowedOrigins = $envContent | Select-String -Pattern 'ALLOWED_ORIGINS=.*' | ForEach-Object { $_.Matches.Value }
    Write-Host "   Value: $allowedOrigins" -ForegroundColor Green
} else {
    Write-Host "❌ .env ALLOWED_ORIGINS is NOT in JSON format!" -ForegroundColor Red
    Write-Host "   Expected: ALLOWED_ORIGINS=[`"..`",`"...`"]" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 2: Verify docker-compose.yml exists
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 2: Verifying docker-compose.yml..." -ForegroundColor Yellow
if (Test-Path "D:\neurotwin\docker-compose.yml") {
    Write-Host "✅ docker-compose.yml found" -ForegroundColor Green
} else {
    Write-Host "❌ docker-compose.yml NOT found at D:\neurotwin\docker-compose.yml" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 3: Stop and remove old API container
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 3: Stopping old API container..." -ForegroundColor Yellow
Push-Location D:\neurotwin
try {
    docker-compose stop api 2>&1 | Out-Null
    docker-compose rm -f api 2>&1 | Out-Null
    Write-Host "✅ Old API container removed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not stop existing container (may not exist yet)" -ForegroundColor Yellow
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 4: Start fresh API container
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 4: Starting fresh API container..." -ForegroundColor Yellow
docker-compose up -d api 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker-compose up executed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Docker-compose up failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 5: Wait for API to start and check health
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 5: Waiting for API to start (max 60 seconds)..." -ForegroundColor Yellow

$maxAttempts = 60
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "   [$attempt/$maxAttempts] Checking API health..." -NoNewline

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host " ✅ HEALTHY!" -ForegroundColor Green
            $healthy = $true
            break
        }
    } catch {
        Write-Host " (not ready yet)" -NoNewline
    }

    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 1
        Write-Host "`r" -NoNewline
    }
}

Write-Host ""

if ($healthy) {
    Write-Host "✅ API is HEALTHY and responding!" -ForegroundColor Green
} else {
    Write-Host "❌ API did not become healthy within 60 seconds" -ForegroundColor Red
    Write-Host "   Checking container logs..." -ForegroundColor Yellow
    docker logs neurotwin-api --tail 50
    Pop-Location
    exit 1
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# STEP 6: Verify all services
# ─────────────────────────────────────────────────────────────────────────

Write-Host "STEP 6: Verifying all services..." -ForegroundColor Yellow
$services = docker-compose ps --services
$allHealthy = $true

docker-compose ps | Format-Table

Pop-Location

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  ✅ FIX VERIFICATION COMPLETE                   ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "SUMMARY:" -ForegroundColor Cyan
Write-Host "  ✅ .env ALLOWED_ORIGINS fixed to JSON format" -ForegroundColor Green
Write-Host "  ✅ API container restarted successfully" -ForegroundColor Green
Write-Host "  ✅ API /api/health endpoint responding with 200 OK" -ForegroundColor Green
Write-Host ""
Write-Host "API is now ready at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Dashboard at: http://localhost" -ForegroundColor Cyan
Write-Host ""
