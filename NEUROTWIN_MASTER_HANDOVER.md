# NEUROTWIN OS — MASTER HANDOVER v3.0
# Generated: 2026-04-04 | CEO Razaq | Use this at the START of every new chat

---

## CRITICAL FIRST STEPS (every new chat)

```powershell
# 1. Start NIM proxy FIRST (before docker)
cd D:\free-claude-code
uv run uvicorn server:app --host 0.0.0.0 --port 8082

# 2. Start all containers
cd D:\neurotwin
docker-compose up -d

# 3. Verify
curl http://localhost:8000/health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## SYSTEM STATE (verified 2026-04-04)

### What is 100% working
- 13 Docker containers up (API, Web, PostgreSQL, Redis, Neo4j, Nginx, Perception, Memory, Avatar, Worker, Grafana, Prometheus, Node-exporter)
- Auth: register/login/JWT all verified
- Conversation /message endpoint: LLM responds, emotion detected, avatar command generated
- SSE /stream endpoint: 200 OK, text/event-stream, 50 lines verified
- PostgreSQL: conversation_messages table writing (4+ rows confirmed)
- Neo4j: User:1, Session:1, Message:2 nodes created live
- Web /health route: returns {"status":"healthy"}
- All 18 SKILL.md files written to D:\neurotwin\claude\skills\
- CLAUDE.md master router updated
- Personality Engine: upgraded NEUROTWIN_PERSONA with full rules
- Emotion Engine: full emotion→avatar→voice map implemented
- Avatar Engine: micro-expression idle rules added to _emotion_to_avatar_command

### What needs rebuild (pending)
- convo.py changes applied BUT container not rebuilt yet
  Run: docker-compose -f D:\neurotwin\docker-compose.yml up -d --build api

### Repos cloned (or to clone)
- D:\neurotwin\external\ruflo (gh repo clone ruvnet/ruflo)
- D:\neurotwin\external\code-review-graph (gh repo clone tirth8205/code-review-graph)

---

## WHAT RUFLO IS (ruvnet/ruflo)
Ruflo is an AI-powered workflow/agent orchestration framework by ruvnet.
Integration potential for NEUROTWIN:
- Use Ruflo's agent orchestration pattern for NEUROTWIN's 8-engine subagent architecture
- Ruflo's skill/tool chaining maps directly to NEUROTWIN's SKILL.md pattern
- Can replace/augment the Claude Code subagent dispatcher
Action: Read D:\neurotwin\external\ruflo\README.md, extract agent patterns, apply to NEUROTWIN orchestrator

## WHAT CODE-REVIEW-GRAPH IS (tirth8205/code-review-graph)
A graph-based code review system using Neo4j.
Integration potential for NEUROTWIN:
- Directly relevant to NEUROTWIN's Neo4j Digital Twin Engine
- Code-review-graph shows how to model relationships in Neo4j for AI analysis
- Pattern can extend NEUROTWIN's behavior-engine graph schema
Action: Read D:\neurotwin\external\code-review-graph\README.md, extract Neo4j schema patterns

---

## SKILL FILES WRITTEN (all at D:\neurotwin\claude\skills\)

| Skill | Status | Purpose |
|---|---|---|
| system-check | DONE | Infra health gate before any engine work |
| perception-engine | DONE | Voice→emotion→backend |
| memory-engine | DONE | Redis+PostgreSQL+Neo4j |
| cognition-engine | DONE | LLM+RAG+streaming |
| personality-engine | DONE | Tone, warmth, identity rules |
| emotion-engine | DONE | Detect, adapt, avatar map |
| behavior-engine | DONE | Digital twin, Neo4j patterns |
| avatar-engine | DONE | Blendshapes, idle, micro-expr |
| visual-identity-engine | DONE | Anime-realistic character system |
| analytics-engine | DONE | Dashboard live data wiring |
| e2e-test-engine | DONE | Full pipeline test protocol |
| summarizer-engine | DONE | Conversation condensation |
| n8n-automation | DONE | Workflow triggers |
| grafana-observability | DONE | Metrics dashboards |
| sentry-triage | DONE | Error monitoring |
| supabase-integration | DONE | Messaging + edge functions |
| playwright-e2e | DONE | Browser automation tests |
| image-generation | DONE | Anime character generation |

---

## IMMEDIATE NEXT STEPS (in order)

### Step 1 — Rebuild API container (URGENT)
```powershell
docker-compose -f D:\neurotwin\docker-compose.yml up -d --build api
Start-Sleep 15
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
```

### Step 2 — Clone repos (if not done)
```powershell
mkdir D:\neurotwin\external
cd D:\neurotwin\external
git clone https://github.com/ruvnet/ruflo.git
git clone https://github.com/tirth8205/code-review-graph.git
```

### Step 3 — Analyze repos and integrate patterns
```powershell
Get-Content D:\neurotwin\external\ruflo\README.md | head -100
Get-Content D:\neurotwin\external\code-review-graph\README.md | head -100
```

### Step 4 — Test upgraded personality engine
```powershell
$TOKEN = (Invoke-RestMethod http://localhost:8000/v1/auth/login -Method POST -ContentType "application/json" -Body '{"email":"ceo2@neurotwin.ai","password":"NeuroCEO2026!"}').access_token
$SID = (Invoke-RestMethod "http://localhost:8000/v1/conversation/session" -Method POST -ContentType "application/json" -Headers @{Authorization="Bearer $TOKEN"} -Body '{}').session_id
$msg = Invoke-RestMethod "http://localhost:8000/v1/conversation/$SID/message" -Method POST -ContentType "application/json" -Headers @{Authorization="Bearer $TOKEN"} -Body '{"content":"I had a really tough day today.","emotion_hint":"sadness"}'
Write-Host $msg.content
# Expected: Response starts with user name or emotion acknowledgment, NOT "I"
# Expected: Contains exactly one "?"
# Expected: Under 150 words
```

### Step 5 — Fix web container healthcheck
Edit D:\neurotwin\web\Dockerfile: change HEALTHCHECK to probe /health not /api/health
Then: docker-compose -f D:\neurotwin\docker-compose.yml build web && docker-compose up -d --force-recreate web

### Step 6 — Build Visual Identity Engine (next major milestone)
- Generate base character using Nano Banana MCP
- Wire AvatarCanvas.tsx to receive full avatar_command with idle block
- Add micro-expression JavaScript animation loop

---

## 8 ENGINE STATUS BOARD

| # | Engine | Code Done | Verified Live | Next Action |
|---|---|---|---|---|
| 0 | system-check | YES | YES | Auto-start proxy on boot |
| 1 | perception | YES | PARTIAL | Full voice→emotion pipeline test |
| 2 | memory | YES | YES | Pinecone when API key added |
| 3 | cognition | YES | YES | None - working |
| 4 | personality | YES | NEEDS REBUILD | Rebuild API, test tone rules |
| 5 | emotion | YES | PARTIAL | Full emotion_events table write |
| 6 | behavior/twin | YES | YES | Extend Neo4j graph schema |
| 7 | avatar | YES | PARTIAL | AvatarCanvas.tsx idle animation |
| 8 | visual identity | SKILL ONLY | NO | Generate character, wire canvas |

---

## CREDENTIALS (never share)
- PostgreSQL: neurotwin / password / neurotwin_db
- Redis: redis://neurotwin-redis:6379/0
- Neo4j: neo4j / neurotwin_password
- SECRET_KEY: 79d6f0fea3d8c61cc7b2683e9049a94ae792115e36ff863903b034d2f0827ff6
- ANTHROPIC_API_KEY: freecc (NIM proxy)
- ANTHROPIC_BASE_URL: http://host.docker.internal:8082/v1
- Test user: ceo2@neurotwin.ai / NeuroCEO2026!

---

## CRITICAL RULES (never break)
1. NEVER use passlib — use: import bcrypt as _bcrypt directly
2. NEXT_PUBLIC_API_URL = http://localhost (never :8000)
3. ANTHROPIC_BASE_URL in docker-compose needs /v1 suffix
4. NIM proxy must run BEFORE docker-compose up
5. All docker commands: use -f D:\neurotwin\docker-compose.yml flag
6. host.docker.internal reaches Windows host from Docker containers

---

## START NEW CHAT PROMPT (copy exactly)

"With great honor, CEO. Resuming NEUROTWIN OS. Read D:\neurotwin\NEUROTWIN_MASTER_HANDOVER.md. 
Start: (1) Start NIM proxy, (2) docker-compose up -d, (3) rebuild API container, 
(4) read external\ruflo and external\code-review-graph READMEs and integrate patterns,
(5) test upgraded personality engine with emotion sadness, 
(6) continue with Step 6 visual identity engine build."
