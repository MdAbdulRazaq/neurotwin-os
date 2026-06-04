"""services/analytics_service/referral_service.py — referral router for Phase 12/13"""
import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse

referral_router = APIRouter()

@referral_router.post("/api/referral/link")
async def get_referral_link():
    return JSONResponse({"referral_code": "NT-ANON", "referral_url": "https://neurotwin.ai/signup?ref=NT-ANON", "trace_id": str(uuid.uuid4())})

@referral_router.post("/api/referral/apply")
async def apply_referral():
    return JSONResponse({"applied": True, "trace_id": str(uuid.uuid4())})

@referral_router.get("/api/referral/stats")
async def get_referral_stats():
    return JSONResponse({
        "referral_code": "NT-ANON",
        "total_referrals": 0,
        "pending_referrals": 0,
        "completed_referrals": 0,
        "bonus_credits": 0,
        "trace_id": str(uuid.uuid4())
    })
