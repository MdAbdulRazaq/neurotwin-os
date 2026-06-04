# NEUROTWIN OS — Resume Script
# Run this at the start of the next chat to verify full state
# Date: 2026-04-03

Write-Host "=== NEUROTWIN OS FULL STATUS CHECK ===" -ForegroundColor Cyan

Write-Host "`n--- 1. CONTAINER STATUS ---" -ForegroundColor Yellow
docker ps --format "table {{.Names}}`t{{.Status}}"

Write-Host "`n--- 2. API HEALTH ---" -ForegroundColor Yellow
try { (Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5).Content } catch { "API not ready: $_" }

Write-Host "`n--- 3. WEB HEALTH ---" -ForegroundColor Yellow
try { (Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 5).Content } catch { "Web health not ready: $_" }

Write-Host "`n--- 4. NIM PROXY (port 8082) ---" -ForegroundColor Yellow
try { (Invoke-WebRequest -Uri "http://localhost:8082/" -UseBasicParsing -TimeoutSec 5).Content } catch { "Proxy DOWN — start it: cd D:\free-claude-code && uv run uvicorn server:app --host 0.0.0.0 --port 8082" }

Write-Host "`n--- 5. DATABASE ROWS ---" -ForegroundColor Yellow
docker exec neurotwin-postgres psql -U neurotwin -d neurotwin_db -c "SELECT 'sessions' as tbl, count(*) FROM sessions UNION ALL SELECT 'messages', count(*) FROM conversation_messages UNION ALL SELECT 'memories', count(*) FROM memories;"

Write-Host "`n--- 6. NEO4J NODES ---" -ForegroundColor Yellow
docker exec neurotwin-neo4j cypher-shell -u neo4j -p neurotwin_password "MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC;" 2>&1

Write-Host "`n--- 7. QUICK END-TO-END TEST ---" -ForegroundColor Yellow
$login = Invoke-RestMethod -Uri "http://localhost:8000/v1/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"ceo2@neurotwin.ai","password":"NeuroCEO2026!"}' -ErrorAction SilentlyContinue
if ($login.access_token) {
    $TOKEN = $login.access_token
    $sess = Invoke-RestMethod -Uri "http://localhost:8000/v1/conversation/session" -Method POST -ContentType "application/json" -Headers @{Authorization="Bearer $TOKEN"} -Body '{}'
    $SID = $sess.session_id
    $msg = Invoke-RestMethod -Uri "http://localhost:8000/v1/conversation/$SID/message" -Method POST -ContentType "application/json" -Headers @{Authorization="Bearer $TOKEN"} -Body '{"content":"System check — are you alive?","emotion_hint":"neutral"}'
    Write-Host "RESPONSE: $($msg.content)" -ForegroundColor Green
    Write-Host "LATENCY : $($msg.latency_ms)ms"
} else {
    Write-Host "Login failed — check API logs: docker logs neurotwin-api --tail 20"
}

Write-Host "`n=== STATUS CHECK COMPLETE ===" -ForegroundColor Cyan
