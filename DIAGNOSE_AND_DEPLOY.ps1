Set-Location D:\neurotwin
$log = "D:\neurotwin\deploy_log.txt"
"NEUROTWIN DEPLOY LOG" | Out-File $log

function Log($msg, $color="White") {
    Write-Host $msg -ForegroundColor $color
    $msg | Out-File $log -Append
}

Log "=== V1.1 DOCKER VERSION ==="
$dv  = docker --version 2>&1
$dcv = docker-compose --version 2>&1
Log "Docker:         $dv"
Log "Docker-Compose: $dcv"

Log "`n=== V1.2 PORT STATUS ==="
foreach ($p in @(80, 3000, 8000, 5432, 6379)) {
    $conn = (Test-NetConnection -ComputerName localhost -Port $p -WarningAction SilentlyContinue -InformationLevel Quiet)
    $label = if ($conn) { "IN USE" } else { "FREE - service may be down" }
    Log "  Port ${p}: $label"
}

Log "`n=== V1.3 ENV VALIDATION ==="
$envContent = Get-Content D:\neurotwin\.env -Raw -ErrorAction SilentlyContinue
if ($envContent) {
    $checks = @(
        @{ key="NEXT_PUBLIC_API_URL=http://localhost"; name="NEXT_PUBLIC_API_URL" },
        @{ key="ANTHROPIC_BASE_URL";                  name="ANTHROPIC_BASE_URL"  },
        @{ key="/v1";                                  name="ANTHROPIC /v1 suffix"},
        @{ key="ALLOWED_ORIGINS=http://localhost,";    name="ALLOWED_ORIGINS comma-format" }
    )
    foreach ($c in $checks) {
        $ok = $envContent.Contains($c.key)
        $status = if ($ok) { "PASS" } else { "FAIL" }
        Log "  [$status] $($c.name)"
    }
} else {
    Log "  FAIL: .env not found"
}

Log "`n=== V2.3 CONTAINER STATUS ==="
$psOut = docker-compose -f D:\neurotwin\docker-compose.yml ps 2>&1
Log $psOut
$problems = $psOut | Select-String "restarting|unhealthy|exited|Exit" -CaseSensitive:$false
if ($problems) {
    Log "PROBLEM CONTAINERS DETECTED:" Red
    $problems | ForEach-Object { Log "  $_" Red }
} else {
    Log "All containers appear healthy" Green
}

Log "`n=== V2.2 REBUILD web + api ==="
Log "Running docker-compose up --build --no-deps web api"
docker-compose -f D:\neurotwin\docker-compose.yml up -d --build --no-deps web api 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) {
    Log "BUILD FAILED - fetching logs" Red
    Log "--- web logs ---"
    docker-compose -f D:\neurotwin\docker-compose.yml logs --tail=60 web 2>&1 | ForEach-Object { Log $_ }
    Log "--- api logs ---"
    docker-compose -f D:\neurotwin\docker-compose.yml logs --tail=60 api 2>&1 | ForEach-Object { Log $_ }
    exit 1
}

Log "`n=== V3.1 WAITING FOR /health ==="
$healthy = $false
for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 4
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Log "API healthy after $($i*4)s: $($r.Content)" Green
            $healthy = $true
            break
        }
    } catch {
        Log "  Waiting $($i*4)s..."
    }
}
if (-not $healthy) {
    Log "API never became healthy - fetching logs" Red
    docker-compose -f D:\neurotwin\docker-compose.yml logs --tail=80 api 2>&1 | ForEach-Object { Log $_ }
    exit 1
}

Log "`n=== V3.2 FRONTEND CHECK ==="
try {
    $r = Invoke-WebRequest -Uri "http://localhost" -TimeoutSec 6 -UseBasicParsing
    Log "Frontend http://localhost - HTTP $($r.StatusCode)" Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    Log "Frontend returned HTTP $code"
}

Log "`n=== V3.3 SWAGGER CHECK ==="
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 5 -UseBasicParsing
    Log "Swagger /docs - HTTP $($r.StatusCode)" Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 401) {
        Log "Swagger /docs - HTTP 401 (auth-gated - expected)" Yellow
    } else {
        Log "Swagger /docs - HTTP $code" Red
    }
}

Log "`n=== V4.1 MASTER VALIDATOR (61 checks) ==="
python D:\neurotwin\services\api\validate_all.py 2>&1 | ForEach-Object { Log $_ }
$validExit = $LASTEXITCODE

Log "`n================================================================"
Log "FINAL SYSTEM REPORT"
Log "================================================================"
Log "  Docker:      $(if ($dv) { 'OK' } else { 'FAIL' })"
Log "  API health:  $(if ($healthy) { 'OK' } else { 'FAIL' })"
Log "  Validator:   $(if ($validExit -eq 0) { 'ALL PASS' } else { 'FAILURES - see above' })"
Log "  Log saved:   $log"
Log "================================================================"

exit $validExit
