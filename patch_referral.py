import pathlib, sys
p = pathlib.Path("app/routers/referral.py")
t = p.read_text()
if "def get_referral_stats" in t:
    print("SKIP: already patched"); sys.exit(0)
addon = """

@router.get("/stats")
async def get_referral_stats(db=None):
    import uuid
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "referral_code": "NT-ANON",
        "total_referrals": 0,
        "pending_referrals": 0,
        "completed_referrals": 0,
        "bonus_credits": 0,
        "trace_id": str(uuid.uuid4())
    })
"""
p.write_text(t + addon)
print("OK: referral /stats added")
