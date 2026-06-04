#############################################################################
# NEUROTWIN OS — Deep Diagnostic Script
# Purpose: Get complete API logs and diagnose real failure
#############################################################################

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        NEUROTWIN OS — Deep API Diagnostic (Last 100 Lines)     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Getting API container logs..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

docker logs neurotwin-api --tail 100

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

Write-Host "Container Status:" -ForegroundColor Yellow
Push-Location D:\neurotwin
docker-compose ps api
Pop-Location

Write-Host ""
Write-Host "⚠️  SEND THIS OUTPUT TO YOUR DEVELOPER" -ForegroundColor Yellow
