# Python PYTHONPATH Fix for Docker Services

## Problem
Services fail with: `ModuleNotFoundError: No module named 'services'`

## Root Cause
Python cannot find the `services` package because it's not in the Python path when the container starts.

## Solution 1: Add PYTHONPATH to docker-compose.yml (QUICKEST)

```yaml
memory:
  build:
    context: .
    dockerfile: ./services/memory/Dockerfile
  container_name: neurotwin-memory
  restart: unless-stopped
  ports:
    - "8002:8002"
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=redis://redis:6379/0
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - PINECONE_API_KEY=${PINECONE_API_KEY}
    - PYTHONPATH=/app:$PYTHONPATH
  depends_on:
    postgres:
      condition: service_healthy

avatar:
  build:
    context: .
    dockerfile: ./services/avatar/Dockerfile
  container_name: neurotwin-avatar
  restart: unless-stopped
  ports:
    - "8003:8003"
  environment:
    - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    - REDIS_URL=redis://redis:6379/0
    - PYTHONPATH=/app:$PYTHONPATH

worker:
  build:
    context: .
    dockerfile: ./services/worker/Dockerfile
  container_name: neurotwin-worker
  restart: unless-stopped
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=redis://redis:6379/0
    - PYTHONPATH=/app:$PYTHONPATH
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```

## Solution 2: Update Service Dockerfiles to Add ENV

**services/memory/Dockerfile**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/memory/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services ./services
COPY services/memory . .
ENV PYTHONPATH=/app:/app/..
EXPOSE 8002
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8002/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

**services/avatar/Dockerfile**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/avatar/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services ./services
COPY services/avatar . .
ENV PYTHONPATH=/app:/app/..
EXPOSE 8003
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8003/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

**services/worker/Dockerfile**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*
COPY services/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services ./services
COPY services/worker . .
ENV PYTHONPATH=/app:/app/..
CMD ["python", "-m", "app.worker"]
```

## Solution 3: Fix Imports in Python Code (BEST LONG-TERM)

Instead of importing from services package, use relative imports:

**services/memory/app/main.py**
```python
from fastapi import FastAPI
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware

# Rest of code...
```

---

## Quick Test

```bash
# After applying fix, rebuild:
docker-compose build --no-cache memory avatar worker

# Start services:
docker-compose up -d memory avatar worker

# Check if they're running:
docker ps | grep -E "memory|avatar|worker"

# Check logs:
docker logs neurotwin-memory
docker logs neurotwin-avatar
docker logs neurotwin-worker

# If still failing, execute bash in container to test:
docker exec -it neurotwin-memory /bin/bash
python -c "from services.common.logging_utils import setup_logging; print('OK')"
```

---

## Which Solution to Use?

| Solution | Pros | Cons | Time |
|----------|------|------|------|
| Solution 1: docker-compose env | Quickest, no rebuild | Temporary | 2 min |
| Solution 2: Dockerfile ENV | Persistent, clean | Rebuild needed | 5 min |
| Solution 3: Fix imports | Best practice | Code changes needed | 15 min |

**Recommendation**: Apply **Solution 1 immediately** to get services running, then implement **Solution 3** for production.
