# DIAGNOSE.ps1
Set-Location D:\neurotwin

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " CONTAINER STATUS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
docker ps -a --format "table {{.Names}}`t{{.Status}}"

$failing = @("neurotwin-memory","neurotwin-avatar","neurotwin-worker","neurotwin-api","neurotwin-action","neurotwin-voice","neurotwin-web")
foreach ($c in $failing) {
    Write-Host "`n--- $c (last 30 lines) ---" -ForegroundColor Yellow
    docker logs $c --tail 30 2>&1
}

Write-Host "`n--- Redis channels ---" -ForegroundColor Yellow
docker exec neurotwin-redis redis-cli PUBSUB CHANNELS 2>&1
