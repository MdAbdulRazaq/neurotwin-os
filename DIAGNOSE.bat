@echo off
cd /d D:\neurotwin
echo ================================================
echo  NEUROTWIN DIAGNOSE
echo ================================================
echo.
echo --- memory ---
docker logs neurotwin-memory --tail 30
echo.
echo --- avatar ---
docker logs neurotwin-avatar --tail 30
echo.
echo --- worker ---
docker logs neurotwin-worker --tail 30
echo.
echo --- api ---
docker logs neurotwin-api --tail 30
echo.
echo --- action ---
docker logs neurotwin-action --tail 30
echo.
echo --- web ---
docker logs neurotwin-web --tail 20
echo.
echo --- neo4j ---
docker logs neurotwin-neo4j --tail 20
echo.
echo ================================================
echo  CONTAINER STATUS
echo ================================================
docker ps --format "table {{.Names}}\t{{.Status}}"
pause
