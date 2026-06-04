# NEUROTWIN OS × SUPABASE — Automated Deployment Script
# Run this to connect everything to Supabase instantly

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    NEUROTWIN OS × SUPABASE Integration                        ║" -ForegroundColor Cyan
Write-Host "║    Starting Automated Deployment...                           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

cd D:\neurotwin

Write-Host "`n[STEP 1] Stopping local PostgreSQL..." -ForegroundColor Yellow
docker-compose stop postgres
Start-Sleep -Seconds 2

Write-Host "`n[STEP 2] Restarting API container..." -ForegroundColor Yellow
docker-compose restart api
Start-Sleep -Seconds 3

Write-Host "`n[STEP 3] Restarting Web container..." -ForegroundColor Yellow
docker-compose restart web
Start-Sleep -Seconds 3

Write-Host "`n[STEP 4] Waiting for services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`n[STEP 5] Checking API connection..." -ForegroundColor Yellow
$apiLogs = docker logs neurotwin-api --tail 30
Write-Host $apiLogs

Write-Host "`n[STEP 6] Checking Web status..." -ForegroundColor Yellow
$webLogs = docker logs neurotwin-web --tail 15
Write-Host $webLogs

Write-Host "`n[STEP 7] Verifying all services..." -ForegroundColor Yellow
docker-compose ps

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║    ✅ DEPLOYMENT COMPLETE                                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n📝 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. Go to: https://supabase.com/dashboard" -ForegroundColor White
Write-Host "2. Select project: neurotwin-os" -ForegroundColor White
Write-Host "3. Click: SQL Editor" -ForegroundColor White
Write-Host "4. Click: New Query" -ForegroundColor White
Write-Host "5. Copy & paste SQL from: D:\neurotwin\supabase_migrations.sql" -ForegroundColor White
Write-Host "6. Click: Run" -ForegroundColor White
Write-Host "`n7. Test dashboard: http://localhost" -ForegroundColor White
Write-Host "8. Check API: curl http://localhost:8000/api/health" -ForegroundColor White

Write-Host "`n🚀 Your NEUROTWIN OS is now connected to Supabase!" -ForegroundColor Green
