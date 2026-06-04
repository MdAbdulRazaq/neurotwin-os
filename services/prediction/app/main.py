"""
NEUROTWIN OS â€” Prediction Agent
FastAPI wrapper around PredictionAgent asyncio loop.
Uvicorn entry: app.main:app  port 8009
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ranker

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware
from services.common.redis_events import publish_event

logger = logging.getLogger("neurotwin.prediction")
setup_logging(service_name="neurotwin.prediction")

REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
PREDICTION_INTERVAL = float(os.getenv("PREDICTION_INTERVAL", "4.0"))


class PredictionAgent:
    def __init__(self):
        self.redis = None
        self.pubsub = None
        self.running = False
        self.emotion_buffer = []
        self.behavior_buffer = []

    async def start(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("neurotwin:emotion", "neurotwin:behavior")
        self.running = True
        asyncio.create_task(self._listen())
        asyncio.create_task(self._predict_loop())
        logger.info("PredictionAgent started")

    async def stop(self):
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()

    async def _listen(self):
        while self.running:
            try:
                msg = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=0.5
                )
                if msg and isinstance(msg.get("data"), str):
                    try:
                        data = json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = None
                    if data and isinstance(data, dict):
                        ch = msg["channel"]
                        if ch == "neurotwin:emotion":
                            self.emotion_buffer.append(data)
                        elif ch == "neurotwin:behavior":
                            self.behavior_buffer.append(data)
                self.emotion_buffer = self.emotion_buffer[-100:]
                self.behavior_buffer = self.behavior_buffer[-100:]
            except Exception as e:
                logger.error(f"Listen error: {e}")
            await asyncio.sleep(0.01)


    def _compute_candidates(self) -> list:
        candidates = []
        hour = datetime.utcnow().hour
        if 0 <= hour < 5:
            candidates.append({"reason": "late_night", "action": "suggest_sleep", "confidence": 0.8})
        recent_neg = [
            e for e in self.emotion_buffer[-10:]
            if e.get("emotion") in ["anger", "sadness", "fear"]
            and e.get("intensity", 0) > 0.6
        ]
        if len(recent_neg) >= 3:
            candidates.append({"reason": "high_stress", "action": "offer_break", "confidence": 0.75})
        if self.behavior_buffer and not any(
            b.get("is_speaking") for b in self.behavior_buffer[-5:]
        ):
            candidates.append({"reason": "post_speech", "action": "follow_up_question", "confidence": 0.7})
        return candidates

    async def _predict_loop(self):
        while self.running:
            try:
                candidates = self._compute_candidates()
                if candidates:
                    try:
                        raw_weights = await self.redis.hgetall("neurotwin:patterns")
                        learned = {}
                        for v in raw_weights.values():
                            d = json.loads(v)
                            learned[d["action"]] = d["weight"]
                    except Exception:
                        learned = {}

                    ctx = {"time_of_day": datetime.utcnow().strftime("%H")}
                    best = ranker.choose_best(candidates, ctx, learned)
                    if best:
                        payload = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "suggestion": best,
                        }
                        await publish_event(
                            channel="neurotwin:suggestions",
                            data=payload,
                            redis_client=self.redis
                        )
                        logger.info(
                            f"suggestion published action={best.get('action')} "
                            f"score={best.get('final_score')}"
                        )
                await asyncio.sleep(PREDICTION_INTERVAL)
            except Exception as e:
                logger.error(f"Predict loop error: {e}")
                await asyncio.sleep(1)



_agent = PredictionAgent()
_redis: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    await _redis.ping()
    await _agent.start(_redis)
    logger.info("Prediction service ready")
    yield
    await _agent.stop()
    await _redis.close()
    logger.info("Prediction service shut down")


app = FastAPI(title="neurotwin-prediction", version="1.0.0", lifespan=lifespan)
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "prediction",
        "running": _agent.running,
        "emotion_buffer": len(_agent.emotion_buffer),
        "behavior_buffer": len(_agent.behavior_buffer),
    }


@app.post("/feedback")
async def feedback(action: str, outcome: str):
    """Accept/reject feedback â€” adjusts ranker shown history."""
    if outcome == "reject":
        ranker._shown_history[action] = 0.0  # reset spam window so it can resurface
    return {"ok": True}

