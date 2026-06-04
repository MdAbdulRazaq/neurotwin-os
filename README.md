# 🧠 NEUROTWIN OS

> **A multimodal digital-twin companion platform** — converses naturally, remembers you, senses your emotional state, displays an expressive avatar, and provides life analytics.

---

## ✨ Features

| Feature | Status |
|---|---|
| 💬 Streaming text chat (SSE) | ✅ MVP |
| 🎙️ Real-time voice (STT + TTS) | ✅ MVP |
| 🧠 Hybrid memory (Redis + Pinecone + Postgres) | ✅ MVP |
| 😊 Emotion detection (voice + text) | ✅ MVP |
| 🎭 3D/2D avatar with lip-sync | ✅ MVP |
| 📊 Analytics dashboard | ✅ MVP |
| 🔒 JWT auth + GDPR controls | ✅ MVP |
| 📱 Flutter mobile app | ✅ MVP |
| 🤖 Behavior modeling (ML Worker) | 🔄 Phase 3 |
| 🕸️ Knowledge graph (Neo4j) | 🔄 Phase 3 |

---

## 🗂️ Repository Structure

```
neurotwin/
├── services/
│   ├── api/           # Core FastAPI backend (LLM, memory, sessions)
│   ├── perception/    # STT, voice emotion detection
│   ├── avatar/        # TTS + lip-sync pipeline
│   ├── memory/        # Embedding + vector DB helpers
│   └── worker/        # ML batch jobs, analytics aggregation
├── web/               # Next.js 14 frontend (React, Three.js)
├── mobile/            # Flutter cross-platform app
├── infra/
│   ├── k8s/           # Kubernetes manifests
│   ├── terraform/     # AWS EKS + RDS + Redis provisioning
│   ├── nginx/         # Reverse proxy config
│   ├── monitoring/    # Prometheus + Grafana config
│   └── sql/           # PostgreSQL init schema
├── .github/workflows/ # CI/CD pipeline (GitHub Actions)
├── docker-compose.yml # Full local dev stack
├── Makefile           # Developer commands
└── .env.example       # Environment variable template
```

---

## 🚀 Quick Start (Local Dev)

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+
- API keys (see `.env.example`)

### 1. Clone & Configure

```bash
git clone https://github.com/yourorg/neurotwin.git
cd neurotwin
make setup          # copies .env.example → .env, installs deps
nano .env           # fill in your API keys
```

### 2. Start Everything

```bash
make dev
```

Services available at:
| Service | URL |
|---|---|
| Web App | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Neo4j Browser | http://localhost:7474 |

### 3. Run Tests

```bash
make test        # backend pytest
make test-web    # frontend type check
```

---

## 🏗️ Architecture

```
User (Browser / Mobile)
        │
        ▼
   Nginx (SSL termination, rate limiting)
        │
        ├── /v1/        → API Service (FastAPI)
        │                   ├── LLM Client (Claude/GPT/Llama)
        │                   ├── Memory Manager (Redis + Pinecone)
        │                   └── Avatar Controller
        │
        ├── /ws/        → WebSocket hub (realtime signaling)
        │
        └── /           → Next.js Web Frontend
                            ├── Three.js Avatar Canvas
                            ├── Streaming Chat UI
                            └── Analytics Dashboard

Background Services:
  • Perception Service → STT (Deepgram/Whisper) + Voice Emotion
  • ML Worker         → Analytics aggregation + Memory consolidation

Data Stores:
  • PostgreSQL   → Users, sessions, messages, memories
  • Redis        → Short-term memory, sessions, rate limiting
  • Pinecone     → Semantic vector memory (embeddings)
  • Neo4j        → Knowledge graph (relationships)
```

---

## 🔑 Required API Keys

| Key | Provider | Used For |
|---|---|---|
| `ANTHROPIC_API_KEY` | [Anthropic](https://console.anthropic.com) | LLM (Claude) |
| `OPENAI_API_KEY` | [OpenAI](https://platform.openai.com) | Embeddings + Whisper STT |
| `PINECONE_API_KEY` | [Pinecone](https://pinecone.io) | Vector memory |
| `ELEVENLABS_API_KEY` | [ElevenLabs](https://elevenlabs.io) | Text-to-speech |
| `DEEPGRAM_API_KEY` | [Deepgram](https://deepgram.com) | Streaming STT |

---

## 🌐 API Reference

### Auth
```
POST /v1/auth/register    → Register new user
POST /v1/auth/login       → Login, get JWT tokens
POST /v1/auth/refresh     → Refresh access token
POST /v1/auth/logout      → Revoke token
DELETE /v1/auth/account   → GDPR: delete account + all data
```

### Conversation
```
POST /v1/conversation/session              → Create session
POST /v1/conversation/{id}/message        → Send message (blocking)
POST /v1/conversation/{id}/stream         → Send message (SSE streaming)
GET  /v1/conversation/{id}/history        → Get message history
```

### Avatar
```
POST /v1/avatar/{id}/speak       → Synthesize TTS + lip-sync data
POST /v1/avatar/{id}/expression  → Set blendshape expression
GET  /v1/avatar/{id}/state       → Current avatar state
GET  /v1/avatar/{id}/audio/{key} → Retrieve cached TTS audio
```

### Memory
```
GET    /v1/memory      → List semantic memories
DELETE /v1/memory      → Delete specific memories (GDPR)
DELETE /v1/memory/all  → Wipe all memory (GDPR)
```

### Analytics
```
GET /v1/analytics/summary?days=7   → Session + engagement stats
GET /v1/analytics/mood?days=30     → Mood timeline
```

---

## 🚢 Production Deployment (Kubernetes)

```bash
# 1. Provision infrastructure
cd infra/terraform
terraform init && terraform plan && terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name neurotwin-cluster --region us-east-1

# 3. Create secrets
kubectl create secret generic neurotwin-secrets \
  --from-literal=DATABASE_URL="..." \
  --from-literal=ANTHROPIC_API_KEY="..." \
  --from-literal=SECRET_KEY="..." \
  -n neurotwin

# 4. Apply manifests
make k8s-apply

# 5. Watch deployment
make k8s-status
```

CI/CD via GitHub Actions automatically:
- Runs lint, type-check, and tests on every PR
- Builds and pushes Docker images to GHCR on merge
- Deploys to staging (develop branch) and production (main branch)
- Rolls back automatically on failure

---

## 💰 Cost Estimates

| Scale | Infra | LLM | TTS/STT | **Total/mo** |
|---|---|---|---|---|
| MVP (10k MAU) | $1,200 | $3,000 | $800 | **~$5,000** |
| Growth (50k MAU) | $4,000 | $12,000 | $3,000 | **~$19,000** |
| Scale (200k MAU) | $12,000 | $40,000 | $10,000 | **~$62,000** |

> LLM costs dominate at scale. Hybrid local (Llama) + cloud (Claude) reduces cost ~40%.

---

## 🗺️ Roadmap

| Phase | Timeline | Focus |
|---|---|---|
| **Phase 0** | Weeks 1–2 | Specs, wireframes, team setup |
| **Phase 1** ✅ | Weeks 3–12 | Text chat, memory, auth, web UI |
| **Phase 2** | Weeks 13–24 | Voice pipeline, avatar, mobile |
| **Phase 3** | Weeks 25–44 | Behavior model, Neo4j, decision sim |
| **Phase 4** | Ongoing | Ops, moderation, data flywheel |

---

## 🔐 Privacy & GDPR

- **Right to access**: `GET /v1/memory` exports all memories
- **Right to erasure**: `DELETE /v1/auth/account` purges Postgres + Pinecone + Redis
- **Local-first mode**: Disable cloud memory via `memory_enabled: false` in preferences
- **Data minimization**: Only embeddings (not raw text) sent to Pinecone by default
- **Encryption**: AES-256 for sensitive DB fields; TLS everywhere
- **Consent**: Explicit opt-in flows for memory storage in onboarding

---

## 🛡️ Security Checklist

- [x] JWT with short expiry (30 min) + refresh token rotation
- [x] Token revocation via Redis blocklist
- [x] Rate limiting (sliding window, per-user)
- [x] Input sanitization + PII scrubbing before LLM calls
- [x] SQL injection prevention (SQLAlchemy ORM)
- [x] CORS locked to allowed origins
- [x] Security headers (HSTS, X-Frame-Options, CSP)
- [x] Non-root Docker containers
- [x] Secrets via K8s secrets / environment (never in code)
- [x] Trivy vulnerability scanning in CI
- [ ] Pen test (scheduled Phase 2)
- [ ] SOC2 audit (Phase 4)

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, Three.js, Framer Motion |
| Mobile | Flutter 3, Dart |
| Backend | Python 3.12, FastAPI, SQLAlchemy async |
| LLM | Claude (Anthropic), GPT-4o (OpenAI), Llama 3 (local) |
| Vector DB | Pinecone |
| Graph DB | Neo4j |
| SQL DB | PostgreSQL 16 |
| Cache | Redis 7 |
| STT | Deepgram Nova-2 / OpenAI Whisper |
| TTS | ElevenLabs Turbo v2 |
| Infra | Docker, Kubernetes (EKS), Terraform |
| CI/CD | GitHub Actions, ArgoCD |
| Monitoring | Prometheus, Grafana, Sentry, OpenTelemetry |

---

## 📄 License

Proprietary — All rights reserved © NEUROTWIN OS
