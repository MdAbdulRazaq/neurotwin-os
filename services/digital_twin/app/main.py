"""
NEUROTWIN Digital Twin — FastAPI Service (Phase 4)
Endpoints: /health, /profile/{user_id}, /predict/{user_id},
           /timeline/{user_id}, /traits/{user_id}, /sync/{user_id}
Port: 8014
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Settings
from .graph import IdentityGraph
from .memory_synthesizer import MemorySynthesizer
from .personality import PersonalityEngine
from .predictor import Predictor
from .profile import ProfileGenerator
from .timeline import Timeline, TimelineEventType
from .event_consumer import TwinEventConsumer
from .logging_utils import setup_logging, generate_trace_id, set_trace_id

setup_logging("digital_twin")
logger = logging.getLogger(__name__)

config  = Settings()

# Global singletons (initialised in lifespan)
_redis:     Optional[aioredis.Redis]    = None
_graph:     Optional[IdentityGraph]     = None
_profile:   Optional[ProfileGenerator] = None
_predictor: Optional[Predictor]        = None
_timeline:  Optional[Timeline]         = None
_consumer:  Optional[TwinEventConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global _redis, _graph, _profile, _predictor, _timeline, _consumer

    _redis = await aioredis.from_url(config.REDIS_URL, decode_responses=True)
    await _redis.ping()

    _graph = IdentityGraph(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)
    await _graph.ensure_indexes()

    personality  = PersonalityEngine(_graph)
    synthesizer  = MemorySynthesizer(_graph, config.PATTERN_TO_TRAIT_THRESHOLD,
                                     config.TRAIT_CONFIDENCE_FLOOR)
    _predictor   = Predictor(_graph)
    _timeline    = Timeline(_graph)
    _profile     = ProfileGenerator(_graph, personality, _predictor, _timeline,
                                    _redis, config.PROFILE_CACHE_TTL)
    _consumer    = TwinEventConsumer(_redis, _graph, personality, synthesizer,
                                     _timeline, config)
    await _consumer.start()
    logger.info("Digital Twin service started")
    yield

    await _consumer.stop()
    await _graph.close()
    await _redis.close()
    logger.info("Digital Twin service stopped")


app = FastAPI(
    title="neurotwin-digital-twin",
    description="Phase 4 — Digital Twin Core",
    version="4.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class SyncRequest(BaseModel):
    user_id:         str
    cognitive_state: Dict[str, float] = {}


@app.get("/health")
async def health():
    if not _redis:
        return {"status": "starting", "service": "digital_twin"}
    try:
        await _redis.ping()
        return {"status": "ok", "service": "digital_twin", "version": "4.0.0"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/profile/{user_id}")
async def get_profile(user_id: str, force_refresh: bool = False):
    """Return the complete digital twin profile for a user."""
    if not _profile:
        raise HTTPException(503, "Service not ready")
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    try:
        await _graph.ensure_user(user_id)
        return await _profile.generate(user_id, force_refresh=force_refresh)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        set_trace_id(None)


@app.get("/predict/{user_id}")
async def predict(user_id: str):
    """Predict the user's next action."""
    if not _predictor or not _graph:
        raise HTTPException(503, "Service not ready")
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    try:
        state = await _graph.get_state(user_id) or {}
        return await _predictor.predict_next_action(user_id, cognitive_state=state)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        set_trace_id(None)


@app.get("/traits/{user_id}")
async def get_traits(user_id: str):
    """Return all personality traits for a user."""
    if not _graph:
        raise HTTPException(503, "Service not ready")
    try:
        traits = await _graph.get_traits(user_id)
        return {"user_id": user_id, "traits": traits, "count": len(traits)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/timeline/{user_id}")
async def get_timeline(user_id: str, limit: int = 30):
    """Return the user's behavioral timeline."""
    if not _timeline:
        raise HTTPException(503, "Service not ready")
    try:
        events = await _timeline.get_recent(user_id, limit=limit)
        delta  = await _timeline.get_state_delta(user_id)
        return {
            "user_id":     user_id,
            "event_count": len(events),
            "events":      events,
            "state_delta": delta,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/sync/{user_id}")
async def sync_twin(user_id: str, req: SyncRequest,
                    background_tasks: BackgroundTasks):
    """
    Full twin sync: update cognitive state → update traits → record timeline.
    Runs graph writes in background, returns immediately.
    """
    if not _graph:
        raise HTTPException(503, "Service not ready")
    trace_id = generate_trace_id()
    set_trace_id(trace_id)

    async def _do_sync():
        set_trace_id(trace_id)
        try:
            await _graph.ensure_user(user_id)
            if req.cognitive_state:
                from .personality import PersonalityEngine as _PE
                pe = PersonalityEngine(_graph)
                await _graph.upsert_state(user_id, req.cognitive_state)
                await pe.update_from_state(user_id, req.cognitive_state)
                await _timeline.record(
                    user_id, TimelineEventType.STATE_CHANGE, req.cognitive_state
                )
            await _profile.invalidate(user_id)
        except Exception as e:
            logger.error("Sync failed", extra={"user_id": user_id, "error": str(e)})
        finally:
            set_trace_id(None)

    background_tasks.add_task(_do_sync)
    return {"status": "sync_queued", "user_id": user_id, "trace_id": trace_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8014, reload=True)
