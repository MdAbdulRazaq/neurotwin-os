Set-Location D:\neurotwin
Write-Host "`n=== STEP 1: Verifying config fix is on disk ===" -ForegroundColor Cyan
$cfg = Get-Content D:\neurotwin\services\api\app\core\config.py -Raw
if ($cfg -match "_FixedEnvSource") {
    Write-Host "  [OK] _FixedEnvSource found in config.py" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] config.py missing fix - aborting" -ForegroundColor Red; exit 1
}

Write-Host "`n=== STEP 2: Copying fixed config.py into container ===" -ForegroundColor Cyan
docker cp D:\neurotwin\services\api\app\core\config.py neurotwin-api:/app/app/core/config.py
if ($LASTEXITCODE -ne 0) { Write-Host "  [FAIL] docker cp failed" -ForegroundColor Red; exit 1 }
Write-Host "  [OK] config.py copied into container" -ForegroundColor Green

Write-Host "`n=== STEP 3: Verifying fix inside container ===" -ForegroundColor Cyan
$test = docker exec neurotwin-api python -c "exec(open('/app/app/core/config.py').read()); print('_FixedEnvSource' in open('/app/app/core/config.py').read())" 2>&1
Write-Host "  Container config check: $test"

Write-Host "`n=== STEP 4: Testing import resolves without pydantic error ===" -ForegroundColor Cyan
$import_test = docker exec neurotwin-api python -c "import sys; sys.path.insert(0,'/app'); from app.core.config import settings; print('ALLOWED_ORIGINS:', settings.ALLOWED_ORIGINS[:2]); print('Settings OK')" 2>&1
Write-Host "  $import_test"
if ($import_test -match "Settings OK") {
    Write-Host "  [OK] Pydantic settings loads cleanly" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Settings import may still have issues - proceeding anyway" -ForegroundColor Yellow
}

Write-Host "`n=== STEP 5: Restarting API container ===" -ForegroundColor Cyan
docker restart neurotwin-api
Write-Host "  Waiting 20 seconds for startup..."
Start-Sleep -Seconds 20

Write-Host "`n=== STEP 6: Confirming API is healthy ===" -ForegroundColor Cyan
$healthy = $false
for ($i = 1; $i -le 8; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host "  [OK] API healthy: $($r.Content)" -ForegroundColor Green
            $healthy = $true; break
        }
    } catch {}
    Write-Host "  Waiting... $($i*3)s"
    Start-Sleep -Seconds 3
}
if (-not $healthy) {
    Write-Host "  [FAIL] API not healthy - fetching logs" -ForegroundColor Red
    docker logs --tail=50 neurotwin-api
    exit 1
}

Write-Host "`n=== STEP 7: Confirming _p12_loaded = True ===" -ForegroundColor Cyan
$p12 = docker exec neurotwin-api python -c "import sys; sys.path.insert(0,'/app'); import app.main as m; print('p12_loaded =', m._p12_loaded)" 2>&1
Write-Host "  $p12"

Write-Host "`n=== STEP 8: Spot-checking failing endpoints ===" -ForegroundColor Cyan
try {
    $r1 = Invoke-WebRequest -Uri "http://localhost/api/referral/stats?user_id=test" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  /api/referral/stats: HTTP $($r1.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  /api/referral/stats: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}
try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  /docs (port 8000): HTTP $($r2.StatusCode)" -ForegroundColor Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Write-Host "  /docs (port 8000): HTTP $code $(if($code -in @(200,401)){'[ACCEPTABLE]'}else{'[FAIL]'})" -ForegroundColor $(if($code -in @(200,401)){"Green"}else{"Red"})
}

Write-Host "`n=== STEP 9: Running master validator (61 checks) ===" -ForegroundColor Cyan
python D:\neurotwin\services\api\validate_all.py
$exit = $LASTEXITCODE

Write-Host "`n================================================================" -ForegroundColor Cyan
if ($exit -eq 0) {
    Write-Host "  61/61 ALL CHECKS PASS - SYSTEM FULLY OPERATIONAL" -ForegroundColor Green
} else {
    Write-Host "  Some checks still failing - review output above" -ForegroundColor Red
}
Write-Host "================================================================`n" -ForegroundColor Cyan
exit $exit
