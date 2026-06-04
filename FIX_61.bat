@echo off
setlocal
cd /d D:\neurotwin
echo.
echo ================================================================
echo   NEUROTWIN OS - FINAL 4-FIX SEQUENCE
echo ================================================================

echo.
echo [FIX 1] Copy syspath fix script into container
docker cp D:\neurotwin\fix_syspath.py neurotwin-api:/app/fix_syspath.py
if %ERRORLEVEL% NEQ 0 ( echo FAIL: docker cp failed && goto DONE )
echo OK

echo.
echo [FIX 2] Run syspath fix inside container
docker exec neurotwin-api python /app/fix_syspath.py
if %ERRORLEVEL% NEQ 0 ( echo WARN: fix script had errors - continuing )

echo.
echo [FIX 3] Copy updated referral_service into container
docker cp D:\neurotwin\services\analytics_service\referral_service.py neurotwin-api:/app/services/analytics_service/referral_service.py
if %ERRORLEVEL% NEQ 0 (
    echo WARN: referral_service copy failed - trying alternate path
    docker exec neurotwin-api find /app -name referral_service.py 2>nul
)

echo.
echo [FIX 4] Restart API container to reload all routes
docker restart neurotwin-api
if %ERRORLEVEL% NEQ 0 ( echo FAIL: docker restart failed && goto DONE )
echo OK - waiting 20 seconds for startup...
timeout /t 20 /nobreak > nul

echo.
echo [CHECK] API health
powershell -Command "try { $r=Invoke-WebRequest -Uri http://localhost:8000/health -TimeoutSec 5 -UseBasicParsing; Write-Host ('Health: HTTP '+$r.StatusCode+' -- '+$r.Content) } catch { Write-Host ('Health check failed: '+$_) }"

echo.
echo [CHECK] Usage status (should be 200)
powershell -Command "try { $r=Invoke-WebRequest -Uri http://localhost/api/usage/status -TimeoutSec 5 -UseBasicParsing; Write-Host ('Usage: HTTP '+$r.StatusCode) } catch { Write-Host ('Usage: '+$_.Exception.Response.StatusCode.value__) }"

echo.
echo [CHECK] Referral stats (should be 200)
powershell -Command "try { $r=Invoke-WebRequest -Uri 'http://localhost/api/referral/stats?user_id=test' -TimeoutSec 5 -UseBasicParsing; Write-Host ('Referral: HTTP '+$r.StatusCode) } catch { Write-Host ('Referral: '+$_.Exception.Response.StatusCode.value__) }"

echo.
echo [CHECK] Events route (405=route exists POST-only, 404=not loaded)
powershell -Command "try { $r=Invoke-WebRequest -Uri http://localhost/api/events -TimeoutSec 5 -UseBasicParsing; Write-Host ('Events: HTTP '+$r.StatusCode) } catch { Write-Host ('Events: HTTP '+$_.Exception.Response.StatusCode.value__) }"

echo.
echo ================================================================
echo   RUNNING MASTER VALIDATOR (61 checks)
echo ================================================================
python D:\neurotwin\services\api\validate_all.py

:DONE
echo.
pause
