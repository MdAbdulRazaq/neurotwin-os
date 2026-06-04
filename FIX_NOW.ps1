# FIX_NOW.ps1 — NEUROTWIN Complete Docker Fix
# Run from D:\neurotwin: powershell -ExecutionPolicy Bypass -File FIX_NOW.ps1

Set-Location D:\neurotwin
$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " NEUROTWIN — FULL DOCKER FIX" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ── STEP 1: Kill everything ──────────────────────────────────────────────────
Write-Host "`n[1/7] Killing all containers..." -ForegroundColor Yellow
$ids = docker ps -aq 2>$null
if ($ids) {
    docker rm -f $ids 2>$null
    Write-Host "  Removed: $($ids -join ', ')" -ForegroundColor Gray
} else {
    Write-Host "  Nothing running." -ForegroundColor Gray
}

# ── STEP 2: Remove old networks ───────────────────────────────────────────────
Write-Host "`n[2/7] Removing old networks..." -ForegroundColor Yellow
docker network rm neurotwin_network 2>$null
Write-Host "  Done." -ForegroundColor Gray

# ── STEP 3: Copy services/common into each service that needs it ─────────────
# This is the REAL fix — avoids sending the entire project as build context.
# Each service builds from its OWN directory + a copy of common/ inside it.
Write-Host "`n[3/7] Copying services/common into service directories..." -ForegroundColor Yellow

$servicesNeedingCommon = @("memory", "avatar", "worker", "voice", "action", "api")
foreach ($svc in $servicesNeedingCommon) {
    $dest = "services\$svc\services\common"
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item "services\common" $dest -Recurse
    Write-Host "  Copied common -> services/$svc/services/common" -ForegroundColor Gray
}

# ── STEP 4: Write self-contained Dockerfiles (context = own dir only) ─────────
Write-Host "`n[4/7] Writing self-contained Dockerfiles..." -ForegroundColor Yellow

# memory
@'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/common ./services/common
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8002/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
'@ | Set-Content "services\memory\Dockerfile" -Encoding UTF8
Write-Host "  memory Dockerfile" -ForegroundColor Gray

# avatar
@'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/common ./services/common
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8003/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
'@ | Set-Content "services\avatar\Dockerfile" -Encoding UTF8
Write-Host "  avatar Dockerfile" -ForegroundColor Gray

# worker
@'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY services/common ./services/common
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
CMD ["python", "-m", "app.worker"]
'@ | Set-Content "services\worker\Dockerfile" -Encoding UTF8
Write-Host "  worker Dockerfile" -ForegroundColor Gray

# voice (no build-essential — pure Python, avoid OOM)
@'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/common ./services/common
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8011
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8011/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
'@ | Set-Content "services\voice\Dockerfile" -Encoding UTF8
Write-Host "  voice Dockerfile" -ForegroundColor Gray

# action
@'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/common ./services/common
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8012
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8012/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012"]
'@ | Set-Content "services\action\Dockerfile" -Encoding UTF8
Write-Host "  action Dockerfile" -ForegroundColor Gray

# api (multi-stage, already correct — just ensure services/common is there)
@'
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY services/common ./services/common
COPY app ./app
ENV PYTHONPATH=/app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
'@ | Set-Content "services\api\Dockerfile" -Encoding UTF8
Write-Host "  api Dockerfile" -ForegroundColor Gray

# ── STEP 5: Write the full docker-compose.yml ─────────────────────────────────
Write-Host "`n[5/7] Writing docker-compose.yml..." -ForegroundColor Yellow

@'
name: neurotwin

networks:
  default:
    name: neurotwin_network
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
  prometheus_data:
  grafana_data:

services:

  postgres:
    image: postgres:16-alpine
    container_name: neurotwin-postgres
    restart: unless-stopped
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: neurotwin
      POSTGRES_PASSWORD: password
      POSTGRES_DB: neurotwin_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neurotwin -d neurotwin_db"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 1G

  redis:
    image: redis:7-alpine
    container_name: neurotwin-redis
    restart: unless-stopped
    ports: ["6379:6379"]
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 512M

  neo4j:
    image: neo4j:5-community
    container_name: neurotwin-neo4j
    restart: unless-stopped
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/neurotwin_password
      NEO4J_dbms_memory_heap_initial__size: 256m
      NEO4J_dbms_memory_heap_max__size: 512m
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:7474 || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 90s
    deploy:
      resources:
        limits:
          memory: 1G

  prometheus:
    image: prom/prometheus:latest
    container_name: neurotwin-prometheus
    restart: unless-stopped
    ports: ["9090:9090"]
    volumes:
      - ./infra/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command: ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus", "--web.enable-lifecycle"]
    deploy:
      resources:
        limits:
          memory: 512M

  grafana:
    image: grafana/grafana:latest
    container_name: neurotwin-grafana
    restart: unless-stopped
    ports: ["3001:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards
    depends_on: [prometheus]
    deploy:
      resources:
        limits:
          memory: 512M

  node-exporter:
    image: prom/node-exporter:latest
    container_name: neurotwin-node-exporter
    restart: unless-stopped
    ports: ["9100:9100"]

  nginx:
    image: nginx:alpine
    container_name: neurotwin-nginx
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./infra/nginx/ssl:/etc/nginx/ssl
    depends_on: [api, web]

  api:
    build:
      context: ./services/api
      dockerfile: Dockerfile
    container_name: neurotwin-api
    restart: unless-stopped
    ports: ["8000:8000"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
      REDIS_URL: redis://neurotwin-redis:6379/0
      NEO4J_URI: bolt://neurotwin-neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: neurotwin_password
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    volumes:
      - ./services/api:/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 1G

  perception:
    build:
      context: ./services/perception
      dockerfile: Dockerfile
    container_name: neurotwin-perception
    restart: unless-stopped
    ports: ["8001:8001"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
    depends_on:
      redis: {condition: service_healthy}
    deploy:
      resources:
        limits:
          memory: 512M

  memory:
    build:
      context: ./services/memory
      dockerfile: Dockerfile
    container_name: neurotwin-memory
    restart: unless-stopped
    ports: ["8002:8002"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
      REDIS_URL: redis://neurotwin-redis:6379/0
      PYTHONPATH: /app
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M

  avatar:
    build:
      context: ./services/avatar
      dockerfile: Dockerfile
    container_name: neurotwin-avatar
    restart: unless-stopped
    ports: ["8003:8003"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      PYTHONPATH: /app
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M

  codereview:
    build:
      context: ./services/codereview
      dockerfile: Dockerfile
    container_name: neurotwin-codereview
    restart: unless-stopped
    ports: ["8004:8004"]
    env_file: .env
    environment:
      NEO4J_URI: bolt://neurotwin-neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: neurotwin_password
      REDIS_URL: redis://neurotwin-redis:6379/0
    depends_on:
      neo4j: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 100s
    deploy:
      resources:
        limits:
          memory: 512M

  visual-identity:
    build:
      context: ./services/visual-identity
      dockerfile: Dockerfile
    container_name: neurotwin-visual-identity
    restart: unless-stopped
    ports: ["8005:8005"]
    env_file: .env
    environment:
      NEO4J_URI: bolt://neurotwin-neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: neurotwin_password
      REDIS_URL: redis://neurotwin-redis:6379/0
    depends_on:
      neo4j: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 100s
    deploy:
      resources:
        limits:
          memory: 512M

  behavior:
    build:
      context: ./services/behavior
      dockerfile: Dockerfile
    container_name: neurotwin-behavior
    restart: unless-stopped
    ports: ["8007:8007"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M

  prediction:
    build:
      context: ./services/prediction
      dockerfile: Dockerfile
    container_name: neurotwin-prediction
    restart: unless-stopped
    ports: ["8009:8009"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8009/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M

  orchestrator:
    build:
      context: ./services/orchestrator
      dockerfile: Dockerfile
    container_name: neurotwin-orchestrator
    restart: unless-stopped
    ports: ["8010:8010"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
      REDIS_URL: redis://neurotwin-redis:6379/0
      NEO4J_URI: bolt://neurotwin-neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: neurotwin_password
      PREDICTION_URL: http://neurotwin-prediction:8009
      ACTION_AGENT_URL: http://neurotwin-action:8012
      VOICE_AGENT_URL: http://neurotwin-voice:8011
    depends_on:
      redis: {condition: service_healthy}
      postgres: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 1536M

  voice:
    build:
      context: ./services/voice
      dockerfile: Dockerfile
    container_name: neurotwin-voice
    restart: unless-stopped
    ports: ["8011:8011"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      PYTHONPATH: /app
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M

  action:
    build:
      context: ./services/action
      dockerfile: Dockerfile
    container_name: neurotwin-action
    restart: unless-stopped
    ports: ["8012:8012"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      PYTHONPATH: /app
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8012/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M

  cognition:
    build:
      context: ./services/cognition
      dockerfile: Dockerfile
    container_name: neurotwin-cognition
    restart: unless-stopped
    ports: ["8013:8013"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8013/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M

  digital_twin:
    build:
      context: ./services/digital_twin
      dockerfile: Dockerfile
    container_name: neurotwin-digital-twin
    restart: unless-stopped
    ports: ["8014:8014"]
    env_file: .env
    environment:
      REDIS_URL: redis://neurotwin-redis:6379/0
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
    depends_on:
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8014/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M

  agents:
    build:
      context: ./services/agents
      dockerfile: Dockerfile
    container_name: neurotwin-agents
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
      REDIS_URL: redis://neurotwin-redis:6379/0
      NEO4J_URI: bolt://neurotwin-neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: neurotwin_password
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
      neo4j: {condition: service_healthy}
    deploy:
      resources:
        limits:
          memory: 1G

  worker:
    build:
      context: ./services/worker
      dockerfile: Dockerfile
    container_name: neurotwin-worker
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://neurotwin:password@neurotwin-postgres:5432/neurotwin_db
      REDIS_URL: redis://neurotwin-redis:6379/0
      PYTHONPATH: /app
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    deploy:
      resources:
        limits:
          memory: 512M

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    container_name: neurotwin-web
    restart: unless-stopped
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_PERCEPTION_WS_URL: ws://localhost:8001
    depends_on: [api]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 512M
'@ | Set-Content "docker-compose.yml" -Encoding UTF8
Write-Host "  docker-compose.yml written." -ForegroundColor Gray

# ── STEP 6: Build one service at a time (avoids WSL2 OOM) ────────────────────
Write-Host "`n[6/7] Building services (sequential to avoid OOM)..." -ForegroundColor Yellow

$buildOrder = @("memory", "avatar", "worker", "voice", "action", "api")
foreach ($svc in $buildOrder) {
    Write-Host "  Building $svc..." -ForegroundColor White
    $result = docker compose build --no-cache $svc 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED: $svc" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        Write-Host "  Continuing anyway..." -ForegroundColor Yellow
    } else {
        Write-Host "  OK: $svc" -ForegroundColor Green
    }
    Start-Sleep -Seconds 3
}

# ── STEP 7: Start everything ──────────────────────────────────────────────────
Write-Host "`n[7/7] Starting all services..." -ForegroundColor Yellow
docker compose up -d --remove-orphans
Write-Host "`nWaiting 90s for neo4j JVM to boot..." -ForegroundColor Yellow
Start-Sleep -Seconds 90

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " FINAL STATUS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
docker ps --format "table {{.Names}}`t{{.Status}}"

Write-Host "`nDone. Run DIAGNOSE.ps1 if anything is unhealthy." -ForegroundColor Cyan
