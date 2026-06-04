# NEUROTWIN OS — MASTER DIAGNOSIS REPORT
# Date: 2026-04-07 | CEO: Abdul Razaq | Machine: DESKTOP-SGEM0PN
# Notion copy: https://www.notion.so/33ba90b899eb81abb42df6510720422f

---

## LIVE SYSTEM — RIGHT NOW (verified this session)

Containers: 16 running
Neo4j:       62 Messages | 17 Sessions | 5 EmotionPatterns | 2 UserMemory | 4 Users
PostgreSQL:  8 users | 22 sessions | 18 messages | 9 emotion_events | 1 insight
Redis:       14 keys (sessions, st:, analytics:, rl:)
Worker:      processing 4 users, batch complete
Agents:      MemoryAgent + EmotionAgent + InsightAgent running, PersonaAgent SQL fixed

---

## ALL COMPLETED WORK

### Infrastructure
[DONE] 16 Docker containers running (api, web, postgres, redis, neo4j, nginx, memory,
       perception, avatar, codereview, visual-identity, agents, worker, prometheus,
       grafana, node-exporter)
[DONE] NIM proxy: D:\ClaudeCode\free-claude-code (stepfun-ai/step-3.5-flash)
[DONE] 7 critical code bugs fixed (IndentationError, SSE format, imports, schema, DB writes)

### 5 Core Steps (AGENTS.md)
[DONE] Step 1: Dashboard wired to real PostgreSQL analytics
[DONE] Step 2: Memory service — Redis short-term + PG long-term + Neo4j graph
[DONE] Step 3: Perception service — DistilBERT-CNN emotion, fixed detect_text(), test PASSED
[DONE] Step 4: Avatar service — Redis-backed blendshape commands, joy->smile verified
[DONE] Step 5: Full E2E streaming test PASSED (SSE 60-85 lines per response)

### 8 Engines
[DONE] Perception:      DistilBERT-CNN, Deepgram/Whisper STT, /v1/emotion/analyze, WS stream
[DONE] Cognition:       LLM SSE streaming, NIM proxy, RAG context injection
[DONE] Memory:          Redis pub/sub, PostgreSQL writes, Neo4j graph, duplicate write fixed
[DONE] Personality:     Full NEUROTWIN_PERSONA with tone variants, rules, twin_profile slot
[DONE] Emotion:         7-emotion map, full avatar_command (blink/eye/head/idle params)
[DONE] Behavior/Twin:   Neo4j behavioral graph, EmotionPattern, UserMemory, InsightAgent
[DONE] Avatar:          Redis-backed service, blendshape commands, Visual Identity enrichment
[DONE] Visual Identity: port 8005, color palette + eye + mouth + skin + special_effects per emotion

### Autonomous Agents
[DONE] MemoryAgent:   listens neurotwin:conversations -> UserMemory nodes in Neo4j
[DONE] EmotionAgent:  listens neurotwin:emotions -> EmotionPattern + calls Visual Identity
[DONE] InsightAgent:  weekly Neo4j analysis -> user_insights table (1 insight stored)
[FIXED] PersonaAgent: SQL bug fixed (messages -> conversation_messages JOIN sessions)

### Infrastructure Improvements
[DONE] Redis pub/sub wired into convo.py (publishes on every message)
[DONE] user_insights PostgreSQL table created
[DONE] Agents Dockerfile + requirements.txt created and deployed
[DONE] Worker Redis URL fixed (redis: -> neurotwin-redis:)
[DONE] 20 SKILL.md files written to D:\neurotwin\claude\skills\
[DONE] CLAUDE.md master router updated with engine routing table
[DONE] Repos cloned: ruflo (259 MCP tools) + code-review-graph (8.2x token reduction)
[DONE] Web Dockerfile healthcheck corrected (/api/health -> /health)
[DONE] user_insights table created in PostgreSQL

---

## FUTURE STEPS (ordered by priority)

### NEXT SESSION — DO THESE FIRST
1. Rebuild agents container (PersonaAgent SQL fix applied):
   docker-compose -f D:\neurotwin\docker-compose.yml up -d --build --force-recreate agents

2. Rebuild web container (healthcheck fix):
   docker-compose -f D:\neurotwin\docker-compose.yml build web
   docker-compose -f D:\neurotwin\docker-compose.yml up -d --force-recreate web

3. Install code-review-graph for Claude Code:
   pip install code-review-graph
   cd D:\neurotwin && code-review-graph install --platform claude-code && code-review-graph build

### SHORT TERM
4. Wire twin_profile dynamically into NEUROTWIN_PERSONA from Neo4j get_user_twin_profile()
5. AvatarCanvas.tsx: consume Visual Identity API (palette, eye_features, special_effects)
6. AvatarCanvas.tsx: implement idle animations (blink_interval_ms, eye_drift_px, breathing)
7. Nano Banana MCP: generate anime character images for joy/sad/surprised/thinking/neutral
8. Perception WebSocket: wire frontend audio -> port 8001 -> emotion -> Redis publish

### MEDIUM TERM
9. Pinecone: add PINECONE_API_KEY to .env -> enable semantic memory recall
10. Ruflo swarm: upgrade subagents to ruflo multi-agent orchestration pattern
11. ElevenLabs TTS: add API key -> wire voice output to avatar lip-sync
12. Deepgram STT: add API key -> enable real voice transcription (currently disabled)
13. Supabase summarize-thread: wire to summarizer-engine for long-term thread summaries
14. Dashboard: show live Neo4j twin profile data (topics, dominant emotion timeline)

### PRODUCTION
15. NIM proxy auto-start: add to Windows startup (Task Scheduler or startup folder)
16. Docker Desktop auto-start: verify it starts on boot
17. K8s/EKS deployment: infra/ manifests exist, ready to apply
18. Sentry: add SENTRY_DSN to .env -> enable error tracking
19. n8n: build emotion spike alert + daily digest workflows
20. Flutter mobile app: D:\neurotwin\mobile\ exists, needs wiring to API

---

## KNOWN ISSUES

| Issue | Severity | Status |
|---|---|---|
| neurotwin-web unhealthy | Cosmetic | Fixed in Dockerfile, needs rebuild |
| NIM proxy dies on restart | Low | Use 1_Start_Proxy_Server.bat on Desktop |
| PersonaAgent wrong SQL | Fixed | Applied, needs agent container rebuild |
| memories table empty | Expected | Normal until Pinecone API key added |
| neurotwin-agents has no healthcheck | Low | Add HEALTHCHECK to agents Dockerfile |

---

## KEY PATHS

D:\neurotwin\                          -- project root
D:\ClaudeCode\free-claude-code\        -- NIM proxy (run 1_Start_Proxy_Server.bat)
D:\neurotwin\docker-compose.yml        -- all 16 containers
D:\neurotwin\CLAUDE.md                 -- master engine router
D:\neurotwin\claude\skills\            -- 20 SKILL.md files
D:\neurotwin\services\agents\          -- 4 autonomous agents
D:\neurotwin\services\visual-identity\ -- Visual Identity Engine
D:\neurotwin\services\codereview\      -- Code Review Engine
D:\neurotwin\external\ruflo\           -- ruflo multi-agent framework
D:\neurotwin\external\code-review-graph\ -- code analysis MCP

---

## NEXT CHAT PROMPT

"Resume NEUROTWIN OS. Read D:\neurotwin\NEUROTWIN_HANDOVER.md.
Rebuild agents container (PersonaAgent SQL fix). Rebuild web container.
Then wire twin_profile dynamically into NEUROTWIN_PERSONA from Neo4j.
Then begin AvatarCanvas.tsx Visual Identity integration."
