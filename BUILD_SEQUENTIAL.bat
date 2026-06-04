@echo off
cd /d D:\neurotwin
echo ================================================
echo  NEUROTWIN — Sequential Build Script
echo  Builds one service at a time to avoid OOM
echo ================================================

echo.
echo [1/4] Building avatar...
docker compose build --no-cache avatar
if %ERRORLEVEL% NEQ 0 ( echo FAILED: avatar & pause & exit /b 1 )
echo [OK] avatar built.

echo.
echo [2/4] Building voice...
docker compose build --no-cache voice
if %ERRORLEVEL% NEQ 0 ( echo FAILED: voice & pause & exit /b 1 )
echo [OK] voice built.

echo.
echo [3/4] Building action...
docker compose build --no-cache action
if %ERRORLEVEL% NEQ 0 ( echo FAILED: action & pause & exit /b 1 )
echo [OK] action built.

echo.
echo [4/4] Building api...
docker compose build --no-cache api
if %ERRORLEVEL% NEQ 0 ( echo FAILED: api & pause & exit /b 1 )
echo [OK] api built.

echo.
echo ================================================
echo  All services built. Starting stack...
echo ================================================
docker compose up -d --remove-orphans

echo.
echo Waiting 90s for neo4j...
timeout /t 90 /nobreak

echo.
echo ================================================
echo  Final status:
echo ================================================
docker ps --format "table {{.Names}}\t{{.Status}}"
pause
