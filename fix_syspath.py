"""
Runs INSIDE the API container (/app/fix_syspath.py).
Patches main.py so Phase 12/13 service imports succeed.
"""
import os, sys

MAIN = "/app/app/main.py"

with open(MAIN) as f:
    src = f.read()

# Strategy 1: replace the os.path.join pattern I added previously
patched = src.replace(
    'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))',
    'sys.path.insert(0, "/app")'
)

# Strategy 2: replace the string-only variant
if patched == src:
    patched = src.replace(
        'os.path.join(os.path.dirname(__file__), "../../../")',
        '"/app"'
    )

# Strategy 3: if no match yet, inject sys.path before the try block
if patched == src:
    if "_p12_loaded" in src and "sys.path" not in src:
        patched = src.replace(
            "\ntry:\n    from services.auth_service",
            '\nsys.path.insert(0, "/app")\ntry:\n    from services.auth_service'
        )

if patched != src:
    with open(MAIN, "w") as f:
        f.write(patched)
    print("FIXED: sys.path patched in main.py")
else:
    print("ALREADY OK or PATTERN MISSING — checking current state:")

# Print relevant lines for diagnosis
with open(MAIN) as f:
    lines = f.readlines()

print("\n--- sys.path / import block in main.py ---")
for i, line in enumerate(lines, 1):
    if any(k in line for k in ["sys.path", "_p12", "from services", "import auth", "import usage", "import share", "import events", "import referral"]):
        print(f"  L{i:03d}: {line.rstrip()}")

# Verify imports actually work now
print("\n--- Import test ---")
sys.path.insert(0, "/app")
try:
    from services.auth_service.main import router as _ar
    print("  auth_service: OK")
except Exception as e:
    print(f"  auth_service: FAIL — {e}")
try:
    from services.usage_service.main import router as _ur
    print("  usage_service: OK")
except Exception as e:
    print(f"  usage_service: FAIL — {e}")
try:
    from services.share_service.main import router as _sr
    print("  share_service: OK")
except Exception as e:
    print(f"  share_service: FAIL — {e}")
try:
    from services.analytics_service.main import router as _er
    print("  analytics_service: OK")
except Exception as e:
    print(f"  analytics_service: FAIL — {e}")
try:
    from services.analytics_service.referral_service import referral_router as _rr
    print("  referral_service: OK")
except Exception as e:
    print(f"  referral_service: FAIL — {e}")
