"""
USAGE SERVICE — Phase 12/13 Continuation
Plan limits, real-time usage counters, simulation grant endpoint.
GET  /api/usage/status   → UrgencyBanner polls this every 2 min
POST /api/usage/grant    → referral bonus injection
"""
import os, logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("neurotwin.usage")
router = APIRouter()

PLAN_LIMITS = {
    "free":  {"simulations": 5,   "memory_entries": 10,  "chat_per_day": 20},
    "pro":   {"simulations": 100, "memory_entries": 500, "chat_per_day": 1000},
    "ultra": {"simulations": -1,  "memory_entries": -1,  "chat_per_day": -1},
}
# INTEGRATION: Replace _usage with Redis GET/INCR using key: usage:{uid}:sims:{month}
_usage: dict = {}

def get_user_usage(user_id: str) -> dict:
    return _usage.get(user_id, {"simulations_used": 0, "chat_used": 0, "memory_used": 0})

class GrantRequest(BaseModel):
    user_id: str
    simulations: int = 0
    source: str = "referral"

@router.get("/api/usage/status")
async def usage_status(request):
    """Returns real-time usage counters for UrgencyBanner. Falls back safely on error."""
    try:
        # INTEGRATION: decode JWT from cookie nt_token and look up real Redis counters
        user_id  = "anonymous"
        plan     = "free"
        limits   = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        usage    = get_user_usage(user_id)
        sims_used  = usage["simulations_used"]
        sims_limit = limits["simulations"]
        pct = 0 if sims_limit == -1 else round(min(sims_used / max(sims_limit, 1) * 100, 100))
        return {
            "user_id": user_id, "plan": plan,
            "simulations": {"used": sims_used, "limit": sims_limit, "pct": pct},
            "chat":        {"used": usage["chat_used"],   "limit": limits["chat_per_day"]},
            "memory":      {"used": usage["memory_used"], "limit": limits["memory_entries"]},
            "warning": pct >= 80,
        }
    except Exception as e:
        logger.error("Usage status error: %s", e)
        return {"plan": "free", "simulations": {"used": 0, "limit": 5, "pct": 0}, "warning": False}

@router.post("/api/usage/grant", status_code=200)
async def grant_usage(body: GrantRequest):
    """Inject bonus simulations (referral reward). INTEGRATION: Redis INCR."""
    _usage.setdefault(body.user_id, {"simulations_used": 0, "chat_used": 0, "memory_used": 0})
    _usage[body.user_id]["simulations_used"] = max(
        0, _usage[body.user_id]["simulations_used"] - body.simulations
    )
    logger.info("Granted %d sims to %s via %s", body.simulations, body.user_id, body.source)
    return {"ok": True, "granted": body.simulations}
