@echo off
echo [NEUROTWIN] Rebuilding API container with all engine upgrades...
cd /d D:\neurotwin
docker-compose -f D:\neurotwin\docker-compose.yml up -d --build api
echo Waiting 20 seconds for container to start...
timeout /t 20 /nobreak
echo Checking health...
curl -s http://localhost:8000/health
echo.
echo [NEUROTWIN] Rebuilding Web container (healthcheck fix)...
docker-compose -f D:\neurotwin\docker-compose.yml build web
docker-compose -f D:\neurotwin\docker-compose.yml up -d --force-recreate web
echo Done! Check: docker ps
pause
