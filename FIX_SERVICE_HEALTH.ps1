# NEUROTWIN OS - Service Health Fix Script
# Implementation of antigravity's proposed changes
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - SERVICE HEALTH FIX" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create Web Health Check Endpoint
Write-Host "[1/3] Creating web health check endpoint..." -ForegroundColor Yellow

# Create the api/health directory
$apiHealthPath = "D:\neurotwin\web\app\api\health"
if (-not (Test-Path $apiHealthPath)) {
    New-Item -ItemType Directory -Path $apiHealthPath -Force | Out-Null
    Write-Host "OK: Created directory" -ForegroundColor Green
}

# Create route.ts
$healthRoute = @'
/**
 * NEUROTWIN OS - Web Health Check Endpoint
 * Returns 200 OK for Docker health checks
 */

export async function GET() {
  const healthStatus = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    service: "neurotwin-web",
    version: "1.0.0",
    uptime: process.uptime(),
  };

  return new Response(JSON.stringify(healthStatus), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
    },
  });
}
'@

$healthRoute | Set-Content "$apiHealthPath\route.ts" -Encoding UTF8
Write-Host "OK: Created health endpoint route.ts" -ForegroundColor Green
Write-Host ""

# Step 2: Verify API config
Write-Host "[2/3] Verifying API configuration..." -ForegroundColor Yellow
$configPath = "D:\neurotwin\services\api\app\core\config.py"
if (Test-Path $configPath) {
    $content = Get-Content $configPath -Raw
    if ($content -match "parse_origins") {
        Write-Host "OK: API config has ALLOWED_ORIGINS validator" -ForegroundColor Green
    }
}
Write-Host ""

# Step 3: Verify .env
Write-Host "[3/3] Verifying .env configuration..." -ForegroundColor Yellow
$envPath = "D:\neurotwin\.env"
$envContent = Get-Content $envPath
$hasOrigins = $envContent | Select-String "ALLOWED_ORIGINS"
if ($hasOrigins) {
    Write-Host "OK: ALLOWED_ORIGINS is configured" -ForegroundColor Green
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FIX COMPLETE - NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Run: docker-compose down" -ForegroundColor White
Write-Host "2. Run: docker-compose up -d --build" -ForegroundColor White
Write-Host "3. Wait 30 seconds" -ForegroundColor White
Write-Host "4. Run: docker ps" -ForegroundColor White
Write-Host ""
Write-Host "Test endpoints:" -ForegroundColor Green
Write-Host "  curl http://localhost:8000/health" -ForegroundColor White
Write-Host "  curl http://localhost:3000/api/health" -ForegroundColor White
Write-Host ""
