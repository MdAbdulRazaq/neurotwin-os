---
name: NEUROTWIN Platform
description: Multimodal digital-twin AI companion platform status and architecture
type: project
---

### Platform Overview
NEUROTWIN OS is a complete microservices platform for AI companion applications with:
- Streaming text chat (SSE)
- Real-time voice (STT + TTS)
- Hybrid memory (Redis + Pinecone + Postgres)
- Emotion detection (voice + text)
- 3D/2D avatar with lip-sync
- Analytics dashboard
- GDPR compliance features

### Current Status (as of March 17, 2026)
**Mission Status:** ✅ FULLY OPERATIONAL - All 12 services healthy
- API Server: Healthy (FastAPI, port 8000)
- Web Frontend: Ready (Next.js 14.2.35, port 3000)
- Perception Service: Healthy (port 8001)
- Memory Service: Healthy (port 8002)
- Avatar Service: Healthy (port 8003)
- PostgreSQL: Healthy (port 5432)
- Redis: Healthy (port 6379)
- Neo4j: Running (ports 7474, 7687)
- Nginx: Running (ports 80, 443)
- Prometheus: Running (port 9090)
- Grafana: Running (port 3001)
- Worker: Running

### Architecture Pattern
User → Nginx → Microservices → Data Stores
- API service handles LLM, memory, sessions
- Web is Next.js frontend with Three.js avatar canvas
- Perception handles STT (Deepgram/Whisper) + voice emotion
- Memory service manages embeddings + Pinecone
- Avatar service provides TTS + lip-sync (ElevenLabs)
- Worker handles ML batch jobs + analytics

### Tech Stack
- Frontend: Next.js 14, React 18, Tailwind, Three.js
- Mobile: Flutter 3
- Backend: Python 3.12, FastAPI, SQLAlchemy async
- LLM: Claude (Anthropic), GPT-4o, Llama 3
- Vector DB: Pinecone
- Graph DB: Neo4j
- SQL DB: PostgreSQL 16
- Cache: Redis 7
- Infra: Docker, Kubernetes (EKS), Terraform
- Monitoring: Prometheus, Grafana, Sentry, OpenTelemetry

### Build Order (Strict)
Must always follow this sequence when building/rebuilding:
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

### Key Recent Changes (March 2026)
- Fixed ALLOWED_ORIGINS CORS configuration (comma-separated format)
- Fixed SQLAlchemy reserved keyword ("metadata" → "metadata_json")
- Added email-validator dependency for Pydantic EmailStr
- Created health check endpoint for Web service
- Fixed nginx.conf to HTTP-only (no SSL requirement in dev)

### Cost Estimates
- MVP (10k MAU): ~$5,000/month
- Growth (50k MAU): ~$19,000/month
- Scale (200k MAU): ~$62,000/month

### Critical Infrastructure URLs
- API: http://localhost:8000
- Web: http://localhost
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090
- Neo4j Browser: http://localhost:7474
- NIM Proxy: http://host.docker.internal:8082/v1

### Test User Credentials
- Email: ceo2@neurotwin.ai
- Password: NeuroCEO2026!

### Important Files
- docker-compose.yml - Full local dev stack
- Makefile - Developer commands (make dev, make test, etc.)
- .env - All secrets and configuration
- infra/ - K8s manifests, Terraform, nginx, monitoring, SQL
- services/ - All 5 microservices + worker
- web/ - Next.js frontend
- mobile/ - Flutter app
- .github/workflows/ - CI/CD pipeline
