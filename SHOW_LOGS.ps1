# NEUROTWIN OS - Detailed Diagnostics
# Shows full logs for debugging

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEUROTWIN OS - API DIAGNOSTICS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "API Container Logs (Last 50 lines):" -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray
docker logs neurotwin-api --tail 50
Write-Host ""
Write-Host ""

Write-Host "Nginx Container Status:" -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray
docker logs neurotwin-nginx --tail 20
Write-Host ""
Write-Host ""

Write-Host "Container Inspection:" -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray
docker ps --no-trunc --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
