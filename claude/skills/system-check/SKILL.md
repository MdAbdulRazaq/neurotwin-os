# SKILL: system-check

## Purpose
Verify full NEUROTWIN OS stack is alive before any engine work begins.

## Scope
All 13 Docker containers, NIM proxy, PostgreSQL, Redis, Neo4j, perception/memory/avatar services.

## Allowed Tools
Desktop Commander, docker ps, curl/Invoke-WebRequest

## Exact Tasks
1. Start NIM proxy: `cd D:\free-claude-code && uv run uvicorn server:app --host 0.0.0.0 --port 8082`
2. Run: `docker ps --format "table {{.Names}}\t{{.Status}}"`
3. Check API: `GET http://localhost:8000/health`
4. Check Web: `GET http://localhost/health`
5. Check Neo4j: `docker exec neurotwin-neo4j cypher-shell -u neo4j -p neurotwin_password "MATCH (n) RETURN count(n);"`

## Pass Criteria
- All 13 containers show "healthy" or "Up"
- API returns `{"status":"ok"}`
- Web returns `{"status":"healthy"}`
- NIM proxy returns `{"status":"ok","provider":"nvidia_nim"}`

## Failure Rule
If any container is down → stop all other engines and fix infrastructure first.

## Output Format
```json
{"system_ready": true, "containers": 13, "api": "ok", "web": "ok", "nim": "ok", "neo4j_nodes": N}
```

## Handoff
Pass system_ready=true to any downstream engine skill.
