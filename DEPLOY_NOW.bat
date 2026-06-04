@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  NEUROTWIN OS — DEPLOY_NOW.bat (FIXED)
REM  Run from cmd.exe: cd D:\neurotwin && DEPLOY_NOW.bat
REM ═══════════════════════════════════════════════════════════════════
cd /d D:\neurotwin

echo.
echo ================================================
echo  STEP 1: Kill ALL containers (including orphans)
echo ================================================
FOR /f "tokens=*" %%i IN ('docker ps -aq') DO docker stop %%i 2>nul
FOR /f "tokens=*" %%i IN ('docker ps -aq') DO docker rm -f %%i 2>nul
echo [OK] All containers removed.

echo.
echo ================================================
echo  STEP 2: Remove old networks
echo ================================================
docker network rm neurotwin_network 2>nul
echo [OK] Network cleanup done.

echo.
echo ================================================
echo  STEP 3: Rebuild broken services (no cache)
echo ================================================
docker compose build --no-cache memory avatar worker action
echo [OK] Services rebuilt.

echo.
echo ================================================
echo  STEP 4: Start all services (remove orphans)
echo ================================================
docker compose up -d --remove-orphans
echo [OK] All services starting...

echo.
echo ================================================
echo  STEP 5: Wait 90s for neo4j JVM to boot
echo ================================================
timeout /t 90 /nobreak

echo.
echo ================================================
echo  STEP 6: Health check
echo ================================================
docker ps --format "table {{.Names}}\t{{.Status}}"

echo.
echo ================================================
echo  DONE. If anything unhealthy: run DIAGNOSE.bat
echo ================================================
pause
