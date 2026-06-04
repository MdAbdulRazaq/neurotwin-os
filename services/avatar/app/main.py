"""
NEUROTWIN OS — Avatar Blendshape Command Service
Publishes avatar expression commands to Redis.
Subscribes to neurotwin:emotion and auto-maps to avatar state.
"""

import json
import logging
import asyncio
from datetime import timedelta
from typing import Optional, Dict, Any

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware
from services.common.redis_events import publish_event

setup_logging(service_name="neurotwin.avatar")
logger = logging.getLogger("neurotwin.avatar")

app = FastAPI(title="neurotwin-avatar", version="1.0.0")
app.add_middleware(TraceMiddleware)

REDIS_URL = "redis://neurotwin-redis:6379/0"

# Emotion → avatar expression mapping
EMOTION_TO_EXPRESSION: Dict[str, str] = {
    "happy": "smile",
    "joy": "smile",
    "excited": "smile",
    "sad": "frown",
    "sadness": "frown",
    "grief": "frown",
    "angry": "intense",
    "anger": "intense",
    "frustrated": "intense",
    "fear": "surprised",
    "surprised": "surprised",
    "disgust": "intense",
    "neutral": "neutral",
    "thinking": "thinking",
    "curious": "thinking",
}

_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def emotion_listener():
    """Background task: subscribe to neurotwin:emotion, map to avatar state, publish neurotwin:avatar_state."""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("neurotwin:emotion")
    logger.info("Avatar emotion listener subscribed to neurotwin:emotion")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            emotion = data.get("emotion", "neutral").lower()
            intensity = float(data.get("intensity", 0.5))
            expression = EMOTION_TO_EXPRESSION.get(emotion, "neutral")

            avatar_state = {
                "expression": expression,
                "intensity": intensity,
                "emotion_source": emotion,
                "blink_rate": "fast" if intensity > 0.7 else "normal",
                "user_id": data.get("user_id"),
                "timestamp": data.get("timestamp"),
            }

            pub = await get_redis()
            await publish_event(channel="neurotwin:avatar_state", data=avatar_state, redis_client=pub)
            logger.info(f"Avatar state published: {expression} (intensity={intensity:.2f}) from emotion={emotion}")

        except Exception as e:
            logger.error(f"Avatar emotion listener error: {e}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(emotion_listener())
    logger.info("Avatar service started — emotion listener running")


@app.on_event("shutdown")
async def shutdown_event():
    global _redis
    if _redis:
        await _redis.close()


@app.get("/health")
async def health():
    try:
        r = await get_redis()
        await r.ping()
        return {"status": "ok", "service": "avatar", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": "avatar", "redis": "disconnected"}


class AvatarCommand(BaseModel):
    expression: str = Field(..., description="Facial expression: neutral, smile, sad, surprised, thinking, excited")
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    blink_rate: str = Field(default="normal")
    eye_focus: str = Field(default="center")
    head_tilt: float = Field(default=0.0, ge=-0.5, le=0.5)
    duration_ms: int = Field(default=1000, ge=10, le=30000)
    blend: bool = Field(default=True)


class CommandResponse(BaseModel):
    status: str
    session_id: str
    stored_key: str
    published_channel: str


@app.post("/v1/avatar/command", response_model=CommandResponse)
async def set_avatar_command(
    command: AvatarCommand,
    session_id: str = Query(..., description="Session ID for command routing")
):
    try:
        r = await get_redis()
        key = f"avatar:{session_id}:command"
        payload = command.dict()
        await r.setex(key, timedelta(seconds=60), json.dumps(payload))
        await publish_event(channel="neurotwin:avatar", data={"session_id": session_id, "command": payload}, redis_client=r)
        logger.info(f"Avatar command for session {session_id}: {command.expression}")
        return CommandResponse(status="ok", session_id=session_id, stored_key=key, published_channel="neurotwin:avatar")
    except Exception as e:
        logger.error(f"Failed to set avatar command: {e}")
        raise HTTPException(status_code=500, detail="Failed to store avatar command")


@app.get("/v1/avatar/command/{session_id}")
async def get_avatar_command(session_id: str):
    try:
        r = await get_redis()
        data = await r.get(f"avatar:{session_id}:command")
        return json.loads(data) if data else None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve avatar command")
