---
name: Critical Rules
description: Essential operational constraints for NEUROTWIN OS
type: reference
---

## Critical Rules - MUST FOLLOW

### 1. ALWAYS run system-check first
Before any engine work, run system-check to verify all services are healthy.

**Why:** Ensures the platform is operational before attempting any feature work.

### 2. NEVER use passlib
Use `import bcrypt as _bcrypt` directly instead of passlib library.

**Why:** Specific compatibility requirement with the existing codebase.

### 3. NEXT_PUBLIC_API_URL configuration
Must be set to `http://localhost` (never `http://localhost:8000`)

**Why:** The frontend should call the nginx proxy on port 80, not bypass to API directly. Nginx handles routing, SSL termination, and load balancing.

**Incorrect:** `NEXT_PUBLIC_API_URL=http://localhost:8000`
**Correct:** `NEXT_PUBLIC_API_URL=http://localhost`

### 4. ANTHROPIC_BASE_URL needs /v1 suffix
In `docker-compose.yml`, ANTHROPIC_BASE_URL must end with `/v1`.

**Why:** The Anthropic SDK expects the full endpoint path including version. Without `/v1`, API calls fail.

**Example:**
```yaml
environment:
  - ANTHROPIC_BASE_URL=http://host.docker.internal:8082/v1
```

### 5. NIM proxy must be running BEFORE API container calls LLM
The Local LLM NIM proxy (on port 8082) must be started before the API container attempts to make LLM calls.

**Why:** API service depends on the NIM proxy for LLM inference. If NIM isn't ready, API requests will fail.

**Sequence:**
1. Start NIM proxy on host (port 8082)
2. Start docker-compose stack
3. API will successfully call LLM through NIM

### 6. Docker commands: use -f D:\neurotwin\docker-compose.yml
All docker-compose commands must explicitly reference the full path to the yml file.

**Why:** Working directory may vary; absolute path ensures correct file is used.

```bash
# Correct
docker-compose -f D:\neurotwin\docker-compose.yml up -d

# Also acceptable (when in project root)
docker-compose up -d
```

### 7. host.docker.internal reaches Windows host from containers
Use `host.docker.internal` when containers need to access services running on the Windows host machine.

**Why:** Docker containers run in isolated network namespace. `host.docker.internal` is a special DNS name that resolves to the host IP from within containers.

**Common use case:** Connecting to locally-running NIM proxy on Windows from API container:
```python
client = Anthropic(
    base_url="http://host.docker.internal:8082/v1",
    api_key="dummy"
)
```

## Docker Compose Notes

- Main file: `D:\neurotwin\docker-compose.yml`
- All 12 services defined (API, Web, Perception, Memory, Avatar, Worker, Postgres, Redis, Neo4j, Nginx, Prometheus, Grafana)
- Health checks configured for all critical services
- Uses Docker networks: `neurotwin_network`
- Volumes for data persistence: postgres_data, redis_data, neo4j_data, etc.

## Environment Variable Format

### ALLOWED_ORIGINS
Must be comma-separated STRING (not JSON):
```
ALLOWED_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8000,https://app.neurotwin.ai
```

The API config has a field validator that splits the string into a list automatically.

## Build Order (Strict)
When rebuilding/constructing the platform, follow exactly:
1. system-check
2. perception-engine
3. memory-engine
4. cognition-engine
5. personality-engine
6. emotion-engine
7. behavior-engine
8. avatar-engine
9. visual-identity-engine
10. analytics-engine
11. summarizer-engine
12. e2e-test-engine

**Never merge engine responsibilities.** Each engine is a separate subagent with its own SKILL.md.
