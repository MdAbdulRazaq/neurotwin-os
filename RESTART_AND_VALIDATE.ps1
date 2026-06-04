Set-Location D:\neurotwin

Write-Host "[1/4] Restarting neurotwin-api and neurotwin-nginx..."
docker restart neurotwin-api
docker restart neurotwin-nginx

Write-Host "[2/4] Waiting 25s for all upstreams to settle..."
Start-Sleep -Seconds 25

Write-Host "[3/4] Confirming services are up..."
# API port 8000
for ($i = 1; $i -le 8; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { Write-Host "  API  :8000/health -> $($r.StatusCode) OK" -ForegroundColor Green; break }
    } catch { Start-Sleep -Seconds 3 }
}
# Web port 3000
for ($i = 1; $i -le 8; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { Write-Host "  Web  :3000/ -> $($r.StatusCode) OK" -ForegroundColor Green; break }
    } catch { Start-Sleep -Seconds 3 }
}

Write-Host "[4/4] Running master validator (61 checks)..."
python D:\neurotwin\services\api\validate_all.py
$exit = $LASTEXITCODE

if ($exit -eq 0) {
    Write-Host "`n  61/61 ALL CHECKS PASS - SYSTEM FULLY OPERATIONAL" -ForegroundColor Green
} else {
    Write-Host "`n  Check FAIL lines above" -ForegroundColor Red
}
exit $exit
