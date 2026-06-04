# NEUROTWIN OS — Manual Implementation Guide

## If FIX_SERVICE_HEALTH.ps1 Doesn't Work

Follow these exact steps manually in PowerShell.

---

## Step 1: Create Web Health Check Directory

```powershell
# Navigate to project
cd D:\neurotwin

# Create the api/health directory
mkdir -Path "D:\neurotwin\web\app\api\health" -Force

# Verify it was created
Get-ChildItem "D:\neurotwin\web\app\api\health"
```

---

## Step 2: Create Health Check Route

**File Location:** `D:\neurotwin\web\app\api\health\route.ts`

**Content to Paste:**

```typescript
/**
 * NEUROTWIN OS — Web Health Check Endpoint
 * Returns 200 OK for Docker health checks
 * Also provides basic system health information
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
```

**PowerShell Command to Create:**

```powershell
$content = @"
/**
 * NEUROTWIN OS — Web Health Check Endpoint
 * Returns 200 OK for Docker health checks
 * Also provides basic system health information
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
"@

$content | Set-Content "D:\neurotwin\web\app\api\health\route.ts" -Encoding UTF8

# Verify
Get-Content "D:\neurotwin\web\app\api\health\route.ts"
```

---

## Step 3: Verify .env ALLOWED_ORIGINS

**File:** `D:\neurotwin\.env`

**Current:**
```
ALLOWED_ORIGINS=http://localhost:3000
```

**Should Be:**
```
ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai
```

**PowerShell Command to Update:**

```powershell
# Read current .env
$envContent = Get-Content "D:\neurotwin\.env"

# Replace ALLOWED_ORIGINS line
$newContent = $envContent -replace 'ALLOWED_ORIGINS=.*', 'ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai'

# Write back
$newContent | Set-Content "D:\neurotwin\.env" -Encoding UTF8

# Verify
Get-Content "D:\neurotwin\.env" | Select-String ALLOWED_ORIGINS
```

---

## Step 4: Restart Docker Services

```powershell
cd D:\neurotwin

# Stop all containers
docker-compose down

# Start with rebuild
docker-compose up -d --build

# Wait for initialization
Start-Sleep -Seconds 30

# Check status
docker ps
```

---

## Step 5: Verify Health Endpoints

```powershell
# Test API health
Write-Host "Testing API health endpoint..."
$apiHealth = Invoke-WebRequest "http://localhost:8000/health" -UseBasicParsing
Write-Host "API Status: $($apiHealth.StatusCode)" -ForegroundColor Green
Write-Host $apiHealth.Content | ConvertFrom-Json | ConvertTo-Json

Write-Host ""

# Test Web health
Write-Host "Testing Web health endpoint..."
$webHealth = Invoke-WebRequest "http://localhost:3000/api/health" -UseBasicParsing
Write-Host "Web Status: $($webHealth.StatusCode)" -ForegroundColor Green
Write-Host $webHealth.Content | ConvertFrom-Json | ConvertTo-Json

Write-Host ""

# Test Nginx proxy
Write-Host "Testing Nginx proxy..."
$nginxTest = Invoke-WebRequest "http://localhost" -UseBasicParsing
Write-Host "Nginx Status: $($nginxTest.StatusCode)" -ForegroundColor Green
```

---

## What Each Fix Does

### Fix #1: Web Health Endpoint

**Problem:** Docker couldn't verify the web container was healthy  
**Solution:** Created `/api/health` endpoint that returns 200 OK  
**Benefit:** Container will now show "healthy" status

### Fix #2: ALLOWED_ORIGINS Environment

**Problem:** Frontend couldn't make CORS requests to API  
**Solution:** Added all necessary origins to `.env`  
**Benefit:** No more CORS errors in browser console

### Fix #3: API Config Validator

**Problem:** ALLOWED_ORIGINS wasn't being parsed from string  
**Solution:** Already present! Config has field_validator  
**Benefit:** Automatically converts "origin1,origin2" to ["origin1", "origin2"]

---

## Troubleshooting

### Issue: "File not found" when creating route.ts

**Solution:** Verify directory exists first
```powershell
Test-Path "D:\neurotwin\web\app\api\health"

# If false, create it:
New-Item -ItemType Directory -Path "D:\neurotwin\web\app\api\health" -Force
```

### Issue: Health check still shows "starting"

**Solution:** Rebuild containers to pick up changes
```powershell
docker-compose down
docker-compose up -d --build
docker wait 30
docker ps
```

### Issue: Web endpoint returns 404

**Solution:** Verify file was created
```powershell
Get-Content "D:\neurotwin\web\app\api\health\route.ts" | head -5
```

### Issue: ALLOWED_ORIGINS still not working

**Solution:** Verify .env was updated
```powershell
Get-Content "D:\neurotwin\.env" | Select-String ALLOWED_ORIGINS
```

---

## Complete Verification

Copy and run this entire script:

```powershell
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   NEUROTWIN OS — SERVICE HEALTH VERIFICATION                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Check 1: Directory exists
Write-Host "`n[Check 1] Web health endpoint directory..."
if (Test-Path "D:\neurotwin\web\app\api\health") {
    Write-Host "✓ Directory exists" -ForegroundColor Green
} else {
    Write-Host "✗ Directory missing" -ForegroundColor Red
}

# Check 2: route.ts exists
Write-Host "`n[Check 2] Route handler file..."
if (Test-Path "D:\neurotwin\web\app\api\health\route.ts") {
    Write-Host "✓ route.ts exists" -ForegroundColor Green
} else {
    Write-Host "✗ route.ts missing" -ForegroundColor Red
}

# Check 3: .env has proper origins
Write-Host "`n[Check 3] ALLOWED_ORIGINS configuration..."
$envOrigins = Get-Content "D:\neurotwin\.env" | Select-String "ALLOWED_ORIGINS"
if ($envOrigins -match "localhost,") {
    Write-Host "✓ ALLOWED_ORIGINS configured" -ForegroundColor Green
    Write-Host "  $($envOrigins.Line)" -ForegroundColor Gray
} else {
    Write-Host "✗ ALLOWED_ORIGINS incomplete" -ForegroundColor Red
}

# Check 4: Containers running
Write-Host "`n[Check 4] Docker containers..."
$containers = docker ps --format "{{.Names}}\t{{.Status}}"
Write-Host $containers
Write-Host ""

# Check 5: Health endpoints
Write-Host "`n[Check 5] Health endpoints..."
try {
    $api = Invoke-WebRequest "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
    Write-Host "✓ API health: $($api.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ API health: unreachable" -ForegroundColor Red
}

try {
    $web = Invoke-WebRequest "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 2
    Write-Host "✓ Web health: $($web.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "✗ Web health: unreachable" -ForegroundColor Red
}

Write-Host "`n" 
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Verification complete! Check results above." -ForegroundColor Yellow
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
```

---

## Next Steps After Fixes

1. ✅ Health checks should pass
2. ✅ Open `http://localhost` in browser
3. ✅ Check browser console for CORS errors (should be none)
4. ✅ Monitor `docker logs neurotwin-web -f`
5. ✅ Monitor `docker logs neurotwin-api -f`

---

**All manual steps are simple copy-paste operations.**  
**No complex syntax required!**
