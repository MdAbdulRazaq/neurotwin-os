@echo off
echo ============================================
echo NEUROTWIN OS — STARTUP SCRIPT
echo ============================================

echo [1/4] Starting NIM Proxy on port 8082...
cd /d D:\free-claude-code
start "NIM Proxy" /MIN cmd /c "uv run uvicorn server:app --host 0.0.0.0 --port 8082"
timeout /t 8 /nobreak >nul

echo [2/4] Cloning external repos (if missing)...
if not exist "D:\neurotwin\external\ruflo" (
    git clone https://github.com/ruvnet/ruflo.git D:\neurotwin\external\ruflo
    echo ruflo cloned.
) else (
    echo ruflo already exists.
)
if not exist "D:\neurotwin\external\code-review-graph" (
    git clone https://github.com/tirth8205/code-review-graph.git D:\neurotwin\external\code-review-graph
    echo code-review-graph cloned.
) else (
    echo code-review-graph already exists.
)

echo [3/4] Starting Docker containers...
cd /d D:\neurotwin
docker-compose -f D:\neurotwin\docker-compose.yml up -d
timeout /t 20 /nobreak >nul

echo [4/4] Verifying system...
curl -s http://localhost:8000/health
curl -s http://localhost/health
curl -s http://localhost:8082/

echo ============================================
echo NEUROTWIN OS — READY
echo Dashboard: http://localhost/dashboard
echo Chat:      http://localhost/chat
echo API:       http://localhost:8000/health
echo ============================================
pause
