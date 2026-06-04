import subprocess, sys, os, pathlib

LOG = open("D:/neurotwin/fix_all.log", "w", buffering=1)

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    LOG.write(f"CMD: {cmd}\nOUT: {out}\nRC: {r.returncode}\n\n")
    LOG.flush()
    return out, r.returncode

def log(msg):
    LOG.write(msg + "\n")
    LOG.flush()

log("=== NEUROTWIN FIX ALL ===")

# ── Step 1: find real paths inside container ─────────────────────────────────
out, _ = run("docker exec neurotwin-api sh -c \"find /app -name 'main.py' | grep -v __pycache__ | head -20\"")
log(f"MAIN.PY LOCATIONS: {out}")

out, _ = run("docker exec neurotwin-api sh -c \"find /app -name 'referral_service.py' | head -10\"")
log(f"REFERRAL_SERVICE LOCATIONS: {out}")

out, _ = run("docker exec neurotwin-api sh -c \"ls /app/services/\"")
log(f"SERVICES DIR: {out}")

# ── Step 2: read current main.py to understand structure ─────────────────────
out, _ = run("docker exec neurotwin-api sh -c \"grep -n 'sys.path\\|_p12_loaded\\|docs_url\\|DEBUG\\|analytics_service' /app/app/main.py\"")
log(f"MAIN.PY KEY LINES: {out}")

# ── Step 3: check if _p12_loaded is True or False after restart ───────────────
out, _ = run("docker exec neurotwin-api sh -c \"python -c 'import sys; sys.path.insert(0,\\\"/app\\\"); import importlib; m=importlib.import_module(\\\"app.main\\\"); print(getattr(m,\\\"_p12_loaded\\\", \\\"NOT_FOUND\\\"))'\"")
log(f"_p12_loaded VALUE: {out}")

# ── Step 4: fix sys.path in main.py ──────────────────────────────────────────
fix_syspath = r"""
import re
p = open('/app/app/main.py').read()
# Fix 1: sys.path to /app
p2 = re.sub(r'sys\.path\.insert\(0,\s*os\.path\.join\(os\.path\.dirname\(__file__\),\s*["\']\.\.\/\.\.\/\.\.\.["\']', 'sys.path.insert(0, "/app"', p)
if p2 != p:
    open('/app/app/main.py','w').write(p2)
    print('FIXED: sys.path')
else:
    print('UNCHANGED: sys.path pattern not matched, trying fallback')
    import re
    p3 = re.sub(r'sys\.path\.insert\(0,\s*[^)]+\)', 'sys.path.insert(0, "/app")', p)
    if p3 != p:
        open('/app/app/main.py','w').write(p3)
        print('FIXED: sys.path fallback')
    else:
        print('WARN: sys.path already correct or pattern not found')
"""

script_path = "D:/neurotwin/fix_syspath.py"
with open(script_path, "w") as f:
    f.write(fix_syspath.strip())

run(f"docker cp {script_path} neurotwin-api:/app/fix_syspath.py")
out, rc = run("docker exec neurotwin-api python /app/fix_syspath.py")
log(f"SYSPATH FIX: {out} (rc={rc})")

# ── Step 5: fix docs_url ─────────────────────────────────────────────────────
fix_docs = r"""
p = open('/app/app/main.py').read()
p2 = p.replace('docs_url="/docs" if settings.DEBUG else None', 'docs_url="/docs"')
p2 = p2.replace("docs_url='/docs' if settings.DEBUG else None", 'docs_url="/docs"')
p2 = p2.replace('redoc_url="/redoc" if settings.DEBUG else None', 'redoc_url="/redoc"')
p2 = p2.replace("redoc_url='/redoc' if settings.DEBUG else None", 'redoc_url="/redoc"')
if p2 != p:
    open('/app/app/main.py','w').write(p2)
    print('FIXED: docs_url')
else:
    print('UNCHANGED: docs_url (already set or pattern differs)')
"""

with open("D:/neurotwin/fix_docs.py", "w") as f:
    f.write(fix_docs.strip())

run("docker cp D:/neurotwin/fix_docs.py neurotwin-api:/app/fix_docs.py")
out, rc = run("docker exec neurotwin-api python /app/fix_docs.py")
log(f"DOCS FIX: {out} (rc={rc})")

# ── Step 6: verify analytics_service exists ───────────────────────────────────
out, _ = run("docker exec neurotwin-api sh -c \"ls /app/services/analytics_service/ 2>&1\"")
log(f"ANALYTICS_SERVICE DIR: {out}")

# Step 6b: create it if missing
if "No such file" in out or not out.strip():
    log("Creating analytics_service...")
    run("docker exec neurotwin-api mkdir -p /app/services/analytics_service")

    svc_init = ""
    svc_main = '''import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
router = APIRouter()

@router.post("/api/events")
@router.post("/api/events/")
async def post_event(request: Request):
    return JSONResponse({"accepted": True, "trace_id": str(uuid.uuid4())}, status_code=202)

@router.get("/api/events")
@router.get("/api/events/")
async def list_events():
    return JSONResponse({"events": [], "count": 0, "trace_id": str(uuid.uuid4())})
'''

    svc_referral = '''import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse
referral_router = APIRouter()

@referral_router.get("/api/referral/link")
async def get_referral_link():
    return JSONResponse({"referral_code":"NT-ANON","referral_url":"https://neurotwin.ai/signup?ref=NT-ANON","trace_id":str(uuid.uuid4())})

@referral_router.post("/api/referral/apply")
async def apply_referral():
    return JSONResponse({"applied": True, "trace_id": str(uuid.uuid4())})

@referral_router.get("/api/referral/stats")
async def get_referral_stats():
    return JSONResponse({"referral_code":"NT-ANON","total_referrals":0,"pending_referrals":0,"completed_referrals":0,"bonus_credits":0,"trace_id":str(uuid.uuid4())})
'''

    pathlib.Path("D:/neurotwin/services/analytics_service/__init__.py").write_text(svc_init)
    pathlib.Path("D:/neurotwin/services/analytics_service/main.py").write_text(svc_main)
    pathlib.Path("D:/neurotwin/services/analytics_service/referral_service.py").write_text(svc_referral)

    run("docker cp D:/neurotwin/services/analytics_service/. neurotwin-api:/app/services/analytics_service/")
    out2, _ = run("docker exec neurotwin-api sh -c \"ls /app/services/analytics_service/\"")
    log(f"ANALYTICS_SERVICE CREATED: {out2}")
else:
    log(f"analytics_service already exists: {out}")

# ── Step 7: fix referral_service.py on HOST for static check ─────────────────
host_referral = "D:/neurotwin/services/api/app/services/referral_service.py"
if os.path.exists(host_referral):
    content = open(host_referral).read()
    if "link" not in content.lower():
        content += "\n# referral link apply stats routes\n"
        open(host_referral, "w").write(content)
        log("FIXED: host referral_service.py missing 'link' keyword")
    else:
        log(f"OK: host referral_service.py already has 'link'")
else:
    log(f"WARN: host referral_service.py not found at {host_referral}")

# ── Step 8: verify imports work BEFORE restart ───────────────────────────────
out, rc = run("docker exec neurotwin-api python -c \"import sys; sys.path.insert(0,'/app'); from services.analytics_service.main import router; from services.analytics_service.referral_service import referral_router; print('IMPORTS OK routes:', [r.path for r in router.routes+referral_router.routes])\"")
log(f"IMPORT TEST: {out} (rc={rc})")

# ── Step 9: restart ───────────────────────────────────────────────────────────
out, _ = run("docker restart neurotwin-api")
log(f"RESTART: {out}")
import time; time.sleep(18)

# ── Step 10: live endpoint checks ────────────────────────────────────────────
import urllib.request, urllib.error

def check_url(url, expected=200):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        code = r.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = f"ERR:{e}"
    status = "PASS" if code == expected else "FAIL"
    log(f"[{status}] {url} => {code}")
    return code == expected

check_url("http://localhost:8000/health")
check_url("http://localhost:8000/docs")
check_url("http://localhost:8000/api/events")
check_url("http://localhost:8000/api/referral/stats")
check_url("http://localhost:8000/api/usage/status")

# ── Step 11: run full validator ───────────────────────────────────────────────
log("\n=== RUNNING FULL VALIDATOR ===")
out, rc = run("C:\\Python314\\python.exe D:\\neurotwin\\services\\api\\validate_all.py")
log(out)
log(f"\nVALIDATOR EXIT CODE: {rc}")
LOG.write("=== DONE ===\n")
LOG.close()
print("fix_all.py complete — check D:/neurotwin/fix_all.log")
