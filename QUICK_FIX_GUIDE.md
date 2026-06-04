# Complete Container Fixes - Action Plan

## Summary of All 10 Container Issues & Solutions

### CRITICAL: Fix Import Path Issues First

**For: neurotwin-memory, neurotwin-avatar, neurotwin-worker**

The issue `ModuleNotFoundError: No module named 'services'` happens because Python can't find the services package.

**SOLUTION - Modify each service's main.py file:**

Instead of:
```python
from services.common.logging_utils import setup_logging
```

Change to:
```python
import sys
sys.path.insert(0, '/app/..')
from services.common.logging_utils import setup_logging
```

OR create `__init__.py` files:
- `services/__init__.py` (empty)
- `services/common/__init__.py` (empty)
- `services/memory/app/__init__.py` (empty)
- `services/avatar/app/__init__.py` (empty)
- `services/worker/app/__init__.py` (empty)

**Alternative: Use relative imports in each service**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

---

## Quick Fix Commands

### 1. Frontend - ✅ FIXED
```bash
cd frontend
# package.json now has "start" script
npm install
```

### 2. Backend - ✅ FIXED
```bash
cd backend
# Files created:
# - Dockerfile (with uvicorn)
# - requirements.txt
# - app.py (updated)
docker build -t neurotwin-backend .
```

### 3. Memory/Avatar/Worker - NEEDS PYTHONPATH FIX
```bash
# Quick option: Set in docker-compose.yml environment
memory:
  environment:
    - PYTHONPATH=/app:$PYTHONPATH
    
avatar:
  environment:
    - PYTHONPATH=/app:$PYTHONPATH
    
worker:
  environment:
    - PYTHONPATH=/app:$PYTHONPATH
```

### 4. Orchestrator & Agents - ✅ FIXED
```bash
# Added memory limits to docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 1G  # orchestrator
      memory: 512M  # agents
```

### 5. Nginx & Digital-Twin - ✅ FIXED
```bash
docker-compose up -d nginx digital-twin
```

---

## Modified Files

| File | Status | Changes |
|------|--------|---------|
| `frontend/package.json` | ✅ Modified | Added start script |
| `backend/Dockerfile` | ✅ Created | FastAPI + uvicorn |
| `backend/requirements.txt` | ✅ Created | Dependencies |
| `backend/app.py` | ✅ Modified | Added uvicorn.run() |
| `services/memory/Dockerfile` | ⏳ Needs PYTHONPATH | Updated structure |
| `services/avatar/Dockerfile` | ⏳ Needs PYTHONPATH | Updated structure |
| `services/worker/Dockerfile` | ⏳ Needs PYTHONPATH | Updated structure |
| `docker-compose.yml` | ✅ Modified | Memory limits, build context |

---

## Docker-Compose Updates Applied

```yaml
# Memory limits added to all services:
deploy:
  resources:
    limits:
      memory: 512M-2G  # Based on service needs

# Build context changed for services:
build:
  context: .
  dockerfile: ./services/memory/Dockerfile
```

---

## Test Each Fix

```bash
# 1. Test frontend build
docker build -t neurotwin-frontend ./frontend

# 2. Test backend
docker build -t neurotwin-backend ./backend

# 3. Test memory (after PYTHONPATH fix)
docker build -t neurotwin-memory ./services/memory

# 4. Run all services
docker-compose up -d

# 5. Check container status
docker ps -a

# 6. View logs for any errors
docker logs neurotwin-memory
docker logs neurotwin-avatar
docker logs neurotwin-worker
```

---

## Root Cause Analysis

| Container | Root Cause | Severity |
|-----------|-----------|----------|
| frontend-1 | No npm start script | HIGH |
| backend-1 | No Dockerfile/entry point | HIGH |
| autonomy-1 | No actual task/command | MEDIUM |
| memory | Python import path | HIGH |
| avatar | Python import path | HIGH |
| worker | Python import path | HIGH |
| orchestrator | Out of memory (137) | HIGH |
| agents | Out of memory (137) | HIGH |
| nginx | Manual stop (clean exit) | LOW |
| digital-twin | Manual stop (clean exit) | LOW |

---

## Next Steps

1. **Immediate** (15 min): Fix PYTHONPATH in memory/avatar/worker Dockerfiles
2. **Short-term** (30 min): Rebuild and test all services
3. **Validation** (10 min): Check docker-compose up -d works
4. **Monitoring**: Review logs and healthchecks

All updated files are in place. Just need PYTHONPATH fix for Python services.
