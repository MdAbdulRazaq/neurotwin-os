"""
NEUROTWIN OS — Cognition Service Entry Point (Phase 3)
Runs the self-learning autonomous cognition engine as a FastAPI app.
Exposes /health, /v1/cognition/state/{user_id}, /v1/cognition/feedback endpoints.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Settings
from .engine import CognitionEngine
from .logging_utils import setup_logging, generate_trace_id, set_trace_id

setup_logging("cognition")
logger = logging.getLogger(__name__)

config  = Settings()
engine: Optional[CognitionEngine] = None


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global engine
    logger.info("Cognition service starting up")
    engine = CognitionEngine(config)
    await engine.start()
    # Run the main cognition loop as a background task
    loop_task = asyncio.create_task(engine.run())
    logger.info("Cognition engine loop started")
    yield
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    await engine.stop()
    logger.info("Cognition service shut down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="neurotwin-cognition",
    description="Phase 3 Self-Learning Autonomous Cognition Engine",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    user_id:       str
    suggestion_id: str
    accepted:      bool
    pattern_type:  Optional[str] = "general"


class PatternRequest(BaseModel):
    user_id:      str
    pattern_type: str
    confidence:   float
    metadata:     Dict[str, Any] = {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — verifies engine and Redis are alive."""
    if not engine or not engine.redis:
        return {"status": "starting", "service": "cognition"}
    try:
        await engine.redis.ping()
        return {"status": "ok", "service": "cognition", "version": "3.0.0"}
    except Exception as e:
        return {"status": "unhealthy", "service": "cognition", "error": str(e)}


@app.get("/v1/cognition/state/{user_id}")
async def get_cognitive_state(user_id: str):
    """Return current cognitive state for a user."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        state = await engine.state_store.get_user_state(user_id)
        stats = await engine.state_store.get_user_stats(user_id)
        return {
            "user_id":   user_id,
            "state":     state.to_dict(),
            "stats": {
                "total_suggestions":  stats.total_suggestions,
                "acceptance_rate":    round(stats.acceptance_rate, 3),
                "accepted":           stats.accepted,
                "rejected":           stats.rejected,
                "last_suggestion_at": stats.last_suggestion_time,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/cognition/patterns/{user_id}")
async def get_patterns(user_id: str):
    """Return all active patterns for a user."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        patterns = await engine.state_store.get_patterns(user_id)
        return {
            "user_id":  user_id,
            "count":    len(patterns),
            "patterns": [p.to_dict() for p in patterns],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/cognition/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit user feedback on a suggestion — drives learning loop."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    try:
        await engine.state_store.record_feedback(
            req.user_id, req.suggestion_id, req.accepted
        )
        await engine.state_store.update_user_stats(req.user_id, accepted=req.accepted)
        await engine.state_store.update_pattern_type_stats(
            req.user_id, req.pattern_type, req.accepted
        )
        await engine.state_model.adjust_from_feedback(req.user_id, req.accepted)
        return {
            "status":    "ok",
            "trace_id":  trace_id,
            "user_id":   req.user_id,
            "accepted":  req.accepted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        set_trace_id(None)


@app.post("/v1/cognition/pattern")
async def inject_pattern(req: PatternRequest):
    """Manually inject a pattern (for testing or external trigger)."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        pattern = await engine.state_store.save_pattern(
            req.user_id, req.pattern_type, req.confidence, req.metadata
        )
        await engine.state_store.mark_user_active(req.user_id)
        return {"status": "ok", "pattern_id": pattern.pattern_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/cognition/suggestions/{user_id}")
async def get_suggestion_history(user_id: str, limit: int = 20):
    """Return recent suggestion history for a user."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        raw = await engine.redis.lrange(
            f"cognition:{user_id}:suggestions", 0, limit - 1
        )
        suggestions = []
        for r in raw:
            try:
                suggestions.append(json.loads(r))
            except Exception:
                continue
        return {"user_id": user_id, "count": len(suggestions), "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8013, reload=True)
