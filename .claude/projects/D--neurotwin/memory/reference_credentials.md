---
name: Stack Credentials
description: Connection strings, URLs, and test user credentials
type: reference
---

## Live Stack Connection Details

### Databases
- **PostgreSQL**
  - Host: localhost (from host), neurotwin-postgres (from containers)
  - Port: 5432
  - User: neurotwin
  - Password: password
  - Database: neurotwin_db
  - Connection URL: `postgresql://neurotwin:password@localhost:5432/neurotwin_db`
  - AsyncPG URL: `postgresql+asyncpg://neurotwin:password@postgres:5432/neurotwin_db` (docker network)

- **Redis**
  - Host: localhost (from host), neurotwin-redis (from containers)
  - Port: 6379
  - URL: `redis://localhost:6379/0`
  - Docker network URL: `redis://redis:6379/0`

- **Neo4j**
  - Host: localhost (from host), neurotwin-neo4j (from containers)
  - Bolt port: 7687
  - HTTP port: 7474
  - User: neo4j
  - Password: neurotwin_password
  - URI: `bolt://neurotwin-neo4j:7687` (docker network)
  - Browser: http://localhost:7474

### API Endpoints (Docker Network)
- **NIM Proxy**: `http://host.docker.internal:8082/v1` - Local LLM inference proxy
- **API Service**: `http://localhost:8000` - FastAPI backend
  - Health: http://localhost:8000/health
  - Docs: http://localhost:8000/docs
- **Web Frontend**: `http://localhost` - Next.js app (nginx proxy)
  - Direct dev: http://localhost:3000
- **Perception Service**: `http://localhost:8001` - STT + voice emotion
- **Memory Service**: `http://localhost:8002` - Embedding + vector DB
- **Avatar Service**: `http://localhost:8003` - TTS + lip-sync
- **Visual Identity Service**: `http://localhost:8005` - Character/avatar design

### Monitoring
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Node Exporter**: http://localhost:9100

### Test User Account
- **Email**: ceo2@neurotwin.ai
- **Password**: NeuroCEO2026!
- **Usage**: For testing authentication, chat sessions, and API flows

### Required API Keys (.env)
These must be added to `.env` file:
```
ANTHROPIC_API_KEY=     # Claude API
OPENAI_API_KEY=        # GPT-4 + Whisper STT
PINECONE_API_KEY=      # Vector database
ELEVENLABS_API_KEY=    # TTS voice synthesis
DEEPGRAM_API_KEY=      # Streaming STT
```

### Docker Compose Configuration
- Primary file: `D:\neurotwin\docker-compose.yml`
- All docker commands should use `-f D:\neurotwin\docker-compose.yml`

### Host Access from Containers
- Windows host reachable via `host.docker.internal` from Docker containers
- Used for NIM proxy (running on Windows at port 8082)
