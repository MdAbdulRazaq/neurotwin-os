"""NEUROTWIN OS - Complete Fix Script - copies ALL services into container and validates."""
import subprocess, sys, time, pathlib, os

ROOT = pathlib.Path(r"D:\neurotwin")
CONTAINER = "neurotwin-api"

def run(cmd, check=True):
    print(f"  $ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(f"    {out}")
    if check and r.returncode != 0:
        print(f"  [WARN] exit code {r.returncode}")
    return r

print("\n" + "="*60)
print("  NEUROTWIN OS - FINAL FIX")
print("="*60)

# Step 1: ensure all service dirs exist in container
print("\n[1] Creating service dirs in container...")
for svc in ["auth_service", "usage_service", "share_service", "analytics_service"]:
    run(f"docker exec {CONTAINER} mkdir -p /app/services/{svc}")

# Step 2: docker cp all service directories
print("\n[2] Copying service files into container...")
for svc in ["auth_service", "usage_service", "share_service", "analytics_service"]:
    src = ROOT / "services" / svc
    if src.exists():
        run(f"docker cp {src} {CONTAINER}:/app/services/")
        print(f"  [OK] {svc} copied")
    else:
        print(f"  [MISSING] {src} - not found on disk!")

# Step 3: verify imports work
print("\n[3] Verifying imports inside container...")
r = run('docker exec neurotwin-api python -c "import sys; sys.path.insert(0,\'/app\'); from services.auth_service.main import router as a; from services.usage_service.main import router as u; from services.share_service.main import router as s; from services.analytics_service.main import router as e; from services.analytics_service.referral_service import referral_router as rr; print(\'ALL IMPORTS OK\', len(a.routes+u.routes+s.routes+e.routes+rr.routes), \'routes\')"', check=False)
if "ALL IMPORTS OK" not in (r.stdout + r.stderr):
    print("  [ERROR] imports still failing - check above output")
else:
    print("  [OK] all Phase 12/13 imports successful")

# Step 4: restart container
print("\n[4] Restarting neurotwin-api...")
run(f"docker restart {CONTAINER}")
print("  Waiting 20 seconds for startup...")
time.sleep(20)

# Step 5: verify _p12_loaded
print("\n[5] Checking _p12_loaded status...")
r = run('docker exec neurotwin-api python -c "import sys; sys.path.insert(0,\'/app\'); import app.main as m; print(\'p12_loaded =\', m._p12_loaded)"', check=False)

# Step 6: run validator
print("\n[6] Running master validator...")
validator = ROOT / "services" / "api" / "validate_all.py"
r = subprocess.run([sys.executable, str(validator)], cwd=str(ROOT))

print("\n" + "="*60)
print("  DONE")
print("="*60)

