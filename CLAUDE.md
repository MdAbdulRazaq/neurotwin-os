# NEUROTWIN OS — CLAUDE.md Master Router
# Version: 2.0 | Updated: 2026-04-04

## SYSTEM IDENTITY
You are the NEUROTWIN OS orchestrator. Every task routes through one of 8 core engines.
Never merge engine responsibilities. One engine = one subagent = one SKILL.md.

## ENGINE ROUTING TABLE

| User Intent | Route To | Skill Path |
|---|---|---|
| system health check | system-check | claude/skills/system-check/SKILL.md |
| voice / emotion detection | perception-engine | claude/skills/perception-engine/SKILL.md |
| memory / recall / context | memory-engine | claude/skills/memory-engine/SKILL.md |
| LLM / reasoning / response | cognition-engine | claude/skills/cognition-engine/SKILL.md |
| tone / personality / warmth | personality-engine | claude/skills/personality-engine/SKILL.md |
| emotion state / mood | emotion-engine | claude/skills/emotion-engine/SKILL.md |
| behavioral model / twin | behavior-engine | claude/skills/behavior-engine/SKILL.md |
| avatar / lip sync / expression | avatar-engine | claude/skills/avatar-engine/SKILL.md |
| character design / anime look | visual-identity-engine | claude/skills/visual-identity-engine/SKILL.md |
| dashboard / metrics | analytics-engine | claude/skills/analytics-engine/SKILL.md |
| full pipeline test | e2e-test-engine | claude/skills/e2e-test-engine/SKILL.md |
| conversation summary | summarizer-engine | claude/skills/summarizer-engine/SKILL.md |

## CRITICAL RULES
1. ALWAYS run system-check first before any engine work
2. NEVER use passlib — use `import bcrypt as _bcrypt` directly
3. NEXT_PUBLIC_API_URL = http://localhost (never :8000)
4. ANTHROPIC_BASE_URL needs /v1 suffix in docker-compose.yml
5. NIM proxy must be running BEFORE API container calls LLM
6. All docker commands: use -f D:\neurotwin\docker-compose.yml
7. host.docker.internal reaches Windows host from containers

## LIVE STACK CREDENTIALS
- PostgreSQL: neurotwin / password / neurotwin_db
- Redis: redis://neurotwin-redis:6379/0
- Neo4j: neo4j / neurotwin_password (bolt://neurotwin-neo4j:7687)
- NIM Proxy: http://host.docker.internal:8082/v1
- API: http://localhost:8000
- Web: http://localhost
- Test User: ceo2@neurotwin.ai / NeuroCEO2026!

## ENGINE BUILD ORDER (strict)
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
