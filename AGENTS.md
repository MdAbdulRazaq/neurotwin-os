# NEUROTWIN OS — Codex MASTER CONTEXT
# READ THIS ENTIRE FILE BEFORE DOING ANYTHING. NO ASSUMPTIONS. NO HALLUCINATIONS.

## MANDATORY RULES
1. Always read actual file contents before editing — never assume
2. Full code at every stage, exact file paths always
3. Rebuild API after Python changes: `docker-compose build api && docker-compose up -d --force-recreate api`
4. Rebuild web after frontend changes: `docker-compose build web && docker-compose up -d --force-recreate web`
5. Working directory: D:\neurotwin\
6. Never skip steps. Never hallucinate.

## STACK
- Backend: FastAPI (Python 3.12) at D:\neurotwin\services\api\app\
- Frontend: Next.js 14 (TypeScript) at D:\neurotwin\web\
- DB: PostgreSQL (local Docker)
- Cache: Redis (local Docker)
- Graph: Neo4j (local Docker)
- Reverse Proxy: Nginx (port 80 — ALL browser traffic goes here)
- LLM: NVIDIA NIM via proxy at http://host.docker.internal:8082


## LLM SETUP (NVIDIA NIM PROXY)
- ANTHROPIC_API_KEY=freecc (fake key — proxy accepts it)
- ANTHROPIC_BASE_URL=http://host.docker.internal:8082 (Docker → Windows host proxy)
- LLM_PROVIDER=anthropic
- LLM_MODEL=Codex-opus-4-6
- Proxy runs on Windows at localhost:8082
- Proxy translates Anthropic format → NVIDIA NIM models
- To start proxy: `cd D:\free-Codex && uv run uvicorn server:app --host 0.0.0.0 --port 8082`

## ALL 12 DOCKER CONTAINERS
neurotwin-api        FastAPI backend           port 8000
neurotwin-web        Next.js frontend          port 3000
neurotwin-nginx      Reverse proxy (MAIN)      port 80
neurotwin-postgres   PostgreSQL                port 5432
neurotwin-redis      Redis cache               port 6379
neurotwin-neo4j      Graph DB                  port 7474/7687
neurotwin-memory     Memory microservice       port 8002
neurotwin-perception Emotion detection         port 8001
neurotwin-avatar     Avatar microservice       port 8003
neurotwin-worker     Background jobs           —
neurotwin-grafana    Monitoring                port 3001
neurotwin-prometheus Metrics                   port 9090

Start all: cd D:\neurotwin && docker-compose up -d
Check:     docker ps --format "table {{.Names}}\t{{.Status}}"

## CREDENTIALS (DO NOT CHANGE)
PostgreSQL: user=neurotwin password=password db=neurotwin_db
Redis:      redis://neurotwin-redis:6379/0
Neo4j:      user=neo4j password=neurotwin_password
SECRET_KEY: 79d6f0fea3d8c61cc7b2683e9049a94ae792115e36ff863903b034d2f0827ff6

## ACCESS URLS
http://localhost/auth/login     ← Main entry (login/register)
http://localhost/chat           ← Chat with NEUROTWIN
http://localhost/dashboard      ← Mind Dashboard
http://localhost:8000/health    ← API health check
http://localhost:7474           ← Neo4j browser
http://localhost:3001           ← Grafana


## PROJECT STRUCTURE (KEY FILES ONLY)
D:\neurotwin\
├── .env                                   ← All secrets + LLM config
├── docker-compose.yml                     ← All 12 services
├── AGENTS.md                              ← THIS FILE
├── services\api\app\
│   ├── main.py                            ← FastAPI + lifespan (memory_manager initialized here)
│   ├── core\
│   │   ├── config.py                      ← Settings with ANTHROPIC_BASE_URL support
│   │   ├── database.py                    ← SQLAlchemy + ORM models
│   │   ├── schemas.py                     ← All Pydantic models
│   │   ├── llm_client.py                  ← LLM client (uses self.anthropic_base)
│   │   ├── memory.py                      ← MemoryManager (Pinecone skipped if no key)
│   │   └── prompts.py                     ← System prompt builder
│   ├── middleware\
│   │   ├── auth.py                        ← JWT auth middleware
│   │   └── rate_limit.py                  ← Rate limiter
│   └── routers\
│       ├── auth.py                        ← Register/Login (bcrypt direct — passlib removed)
│       ├── convo.py                       ← Sessions + streaming chat
│       ├── memory.py                      ← Memory CRUD
│       ├── analytics.py                   ← Dashboard data
│       ├── avatar.py                      ← Avatar control
│       └── user.py                        ← Profile
└── web\
    ├── .env.local                         ← NEXT_PUBLIC_API_URL=http://localhost
    └── app\
        ├── auth\login\page.tsx            ← Login + Register (working)
        ├── chat\page.tsx                  ← Chat (FULLY WIRED — auth guard + SSE streaming)
        └── dashboard\page.tsx             ← Dashboard (needs real data wiring)
    └── lib\
        ├── api.ts                         ← Axios client + authApi + token management
        ├── types.ts                       ← All TypeScript interfaces
        ├── hooks\useConversation.ts       ← SSE streaming hook (COMPLETE)
        ├── hooks\useVoice.ts              ← Voice/mic hook
        └── stores\avatarStore.ts          ← Zustand avatar state
    └── components\
        ├── avatar\AvatarCanvas.tsx        ← Three.js 3D procedural avatar
        ├── chat\MessageBubble.tsx         ← Message component
        ├── chat\EmotionIndicator.tsx      ← Emotion badge
        └── voice\VoiceControl.tsx         ← Voice UI


## WHAT IS COMPLETE (DO NOT REBUILD THESE)
- [x] All 12 Docker containers running
- [x] PostgreSQL tables: users, sessions, conversation_messages, memories, emotion_events
- [x] Security: JWT revocation, brute-force lockout, IDOR fix, rate limiting
- [x] Auth: register + login working (bcrypt 5.0.0 fixed — passlib replaced)
- [x] CORS: all calls via nginx port 80 (NEXT_PUBLIC_API_URL=http://localhost)
- [x] Chat page: fully wired SSE streaming + auth guard + error handling
- [x] 3D avatar: Three.js procedural head with emotion expressions
- [x] MemoryManager: initialized in lifespan startup (main.py)
- [x] LLM client: custom ANTHROPIC_BASE_URL support for NVIDIA NIM proxy
- [x] Pinecone: gracefully skipped when PINECONE_API_KEY not set

## REMAINING STEPS (DO THESE IN ORDER)

### STEP 1 — WIRE DASHBOARD TO REAL API DATA ← START HERE
File to fix:  D:\neurotwin\web\app\dashboard\page.tsx
API router:   D:\neurotwin\services\api\app\routers\analytics.py
Problem:      Dashboard shows empty/placeholder data — analytics router may return stub data
Goal:         Real session counts, message counts, mood timeline, top topics from DB
How:          1. Read analytics.py to see what queries exist
              2. Read dashboard\page.tsx to see what it expects
              3. Fix the analytics queries to pull real data from PostgreSQL
              4. Rebuild web if needed

### STEP 2 — MEMORY SERVICE WIRING
File: D:\neurotwin\services\api\app\core\memory.py
File: D:\neurotwin\services\api\app\routers\memory.py
Goal: Conversation history feeds back correctly into LLM prompts via Redis short-term memory
Test: Send 3 messages, ask "what did I say first?" — should remember

### STEP 3 — PERCEPTION SERVICE (EMOTION DETECTION)
File: D:\neurotwin\web\lib\hooks\useVoice.ts
File: D:\neurotwin\services\api\app\routers\convo.py
Goal: Emotion detected from voice feeds into conversation context + avatar expression
Note: neurotwin-perception runs at port 8001

### STEP 4 — AVATAR SERVICE INTEGRATION
File: D:\neurotwin\web\components\avatar\AvatarCanvas.tsx
File: D:\neurotwin\services\api\app\routers\avatar.py
Goal: LLM response avatar_command drives real blendshape expressions on the 3D head

### STEP 5 — END-TO-END STREAMING TEST
Goal: Full flow confirmed — login → session → message → SSE tokens → avatar reacts
Use: docker logs neurotwin-api + browser DevTools Network tab

## IMPORTANT TECHNICAL FACTS
1. bcrypt: passlib replaced — auth.py uses `import bcrypt as _bcrypt` directly
2. LLM base URL: self.anthropic_base (not self.ANTHROPIC_BASE) in llm_client.py
3. CORS: browser must use http://localhost — NOT http://localhost:8000
4. memory_manager: initialized in lifespan in main.py — do not remove this
5. Pinecone: wrapped in try/except — safe to run without PINECONE_API_KEY
6. Docker internal host: use host.docker.internal to reach Windows host from container

## DIAGNOSTIC COMMANDS
docker ps --format "table {{.Names}}\t{{.Status}}"
docker logs neurotwin-api --tail 40
docker logs neurotwin-web --tail 20
docker-compose build api && docker-compose up -d --force-recreate api
docker-compose build web && docker-compose up -d --force-recreate web
docker exec neurotwin-postgres psql -U neurotwin -d neurotwin_db -c "SELECT count(*) FROM users;"

## HOW TO USE THIS FILE
Codex reads AGENTS.md automatically when started in D:\neurotwin\.
Always tell Codex which STEP to work on.
Codex must read the actual source files before writing any code.
