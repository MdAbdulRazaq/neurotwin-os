# NEUROTWIN OS — Implementation Plan: Service Health Fix
## By antigravity | Executed by Assistant

---

## Executive Summary

The API and Web containers are showing "health: starting" status because they lack proper health check endpoints. This document details the exact fixes required and how to implement them.

**Status:** ✅ **READY TO IMPLEMENT**
- ✓ nginx.conf fixed (HTTP-only, no SSL errors)
- ✓ .env updated with proper ALLOWED_ORIGINS
- ⏳ Web health endpoint ready to deploy
- ✓ API already has proper config validation

---

## Root Causes

| Service | Issue | Impact |
|---------|-------|--------|
| API | Docker health check fails | Container shows "health: starting" |
| Web | Missing `/api/health` endpoint | Docker can't verify health |
| Config | ALLOWED_ORIGINS wasn't being parsed | CORS errors possible |

---

## Proposed Solution

### [1] API Service Configuration ✓ ALREADY FIXED

**File:** `D:\neurotwin\services\api\app\core\config.py`

**Current Status:** The config already has the proper field_validator!

```python
@field_validator("ALLOWED_ORIGINS", mode="before")
@classmethod
def parse_origins(cls, v):
    if isinstance(v, str):
        return [o.strip() for o in v.split(",")]
    return v
```

**What it does:**
- Accepts comma-separated string from environment
- Splits and trims each origin
- Returns proper List[str] to Pydantic

**Example:**
```
Input:  "http://localhost,http://localhost:3000,https://app.neurotwin.ai"
Output: ["http://localhost", "http://localhost:3000", "https://app.neurotwin.ai"]
```

---

### [2] Web Frontend Health Check ⏳ READY TO DEPLOY

**File to Create:** `D:\neurotwin\web\app\api\health\route.ts`

**Directory Structure:**
```
web/
├── app/
│   ├── api/                    [NEW]
│   │   └── health/             [NEW]
│   │       └── route.ts        [NEW]
│   ├── auth/
│   ├── chat/
│   └── dashboard/
```

**Content:**
```typescript
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

**What it does:**
- Responds to GET requests at `/api/health`
- Returns 200 OK (satisfies Docker health check)
- Provides system information

**Docker Dockerfile Check:**
```dockerfile
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

### [3] Environment Configuration ✓ UPDATED

**File:** `D:\neurotwin\.env`

**Change Made:**
```diff
- ALLOWED_ORIGINS=http://localhost:3000
+ ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai
```

**Why Multiple Origins:**
| Origin | Purpose |
|--------|---------|
| `http://localhost` | Nginx proxy (port 80) |
| `http://localhost:3000` | Next.js dev server (direct) |
| `http://localhost:8000` | API for CORS requests |
| `https://app.neurotwin.ai` | Production domain |

---

## Implementation Steps

### Step 1: Run PowerShell Fix Script
```powershell
cd D:\neurotwin
.\FIX_SERVICE_HEALTH.ps1
```

This script will:
- Create the `web/app/api/health/` directory structure
- Create the `route.ts` health check endpoint
- Verify all configurations
- Display next steps

### Step 2: Rebuild Containers
```powershell
cd D:\neurotwin

# Stop all containers
docker-compose down

# Rebuild images (picks up config changes)
docker-compose up -d --build

# Wait 30 seconds for initialization
Start-Sleep -Seconds 30
```

### Step 3: Verify Health Status
```powershell
# Check all containers
docker ps

# Expected output: All containers showing "healthy" or "Up"
```

### Step 4: Test Health Endpoints
```powershell
# Test API health
curl http://localhost:8000/health

# Test Web health
curl http://localhost:3000/api/health

# Test Nginx proxy
curl http://localhost/api/health

# Check CORS headers
curl -H "Origin: http://localhost:3000" -i http://localhost:8000/health
```

---

## Expected Results

### Before Fix:
```
docker ps

CONTAINER ID   IMAGE              STATUS
abc123         neurotwin-api      Up 5m (health: starting)
def456         neurotwin-web      Up 5m (health: starting)
ghi789         neurotwin-nginx    Up 5m
```

### After Fix:
```
docker ps

CONTAINER ID   IMAGE              STATUS
abc123         neurotwin-api      Up 5m (healthy)
def456         neurotwin-web      Up 5m (healthy)
ghi789         neurotwin-nginx    Up 5m
```

---

## Verification Checklist

- [ ] Created `web/app/api/health/route.ts`
- [ ] Updated `.env` ALLOWED_ORIGINS
- [ ] Ran `docker-compose down`
- [ ] Ran `docker-compose up -d`
- [ ] All containers show "healthy" in `docker ps`
- [ ] API responds at `http://localhost:8000/health`
- [ ] Web responds at `http://localhost:3000/api/health`
- [ ] Browser loads `http://localhost`
- [ ] No CORS errors in browser console

---

## Rollback (If Needed)

If any issue occurs:

```powershell
# Stop and remove all containers
docker-compose down -v

# Restore original .env (no changes actually harmful)
git checkout D:\neurotwin\.env

# Restart
docker-compose up -d
```

---

## Technical Details

### ALLOWED_ORIGINS Field Validator

**Location:** `services/api/app/core/config.py:98-103`

The field validator uses Pydantic's `mode="before"` to process the environment variable **before** JSON parsing. This allows flexible input formats:

```python
@field_validator("ALLOWED_ORIGINS", mode="before")
@classmethod
def parse_origins(cls, v):
    if isinstance(v, str):
        return [o.strip() for o in v.split(",")]
    return v
```

**Handles:**
- ✓ Comma-separated strings: `"http://localhost,http://localhost:3000"`
- ✓ Already-parsed lists: `["http://localhost"]`
- ✓ Whitespace: `"http://localhost , http://localhost:3000"`

---

## Summary

| Component | Status | Change | Impact |
|-----------|--------|--------|--------|
| **API Config** | ✓ | No change needed | Validator already in place |
| **Web Health** | ⏳ | Add route.ts | Enables health checks |
| **Environment** | ✓ | Update ALLOWED_ORIGINS | Fixes CORS |
| **Nginx** | ✓ | Already fixed | HTTP-only, no SSL errors |

---

**Implementation Date:** March 15, 2026  
**Status:** Ready for deployment  
**Risk Level:** LOW (Non-breaking changes, additive only)

---
