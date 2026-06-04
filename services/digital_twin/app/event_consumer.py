"""
NEUROTWIN Digital Twin — Event Consumer (Phase 4)
Listens to Redis Pub/Sub channels, drives graph + personality + timeline updates.
No blocking calls. trace_id on every message.
"""
import asyncio
import json
import logging
from typing import Any, Dict

import redis.asyncio as aioredis

from .config import Settings
from .graph import IdentityGraph
from .memory_synthesizer import MemorySynthesizer
from .personality import PersonalityEngine
from .timeline import Timeline, TimelineEventType
from .logging_utils import generate_trace_id, set_trace_id

logger = logging.getLogger(__name__)


class TwinEventConsumer:
    def __init__(self, redis: aioredis.Redis, graph: IdentityGraph,
                 personality: PersonalityEngine, synthesizer: MemorySynthesizer,
                 timeline: Timeline, config: Settings):
        self.redis       = redis
        self.graph       = graph
        self.personality = personality
        self.synthesizer = synthesizer
        self.timeline    = timeline
        self.config      = config
        self.running     = False
        self._task       = None

    async def start(self):
        self.running = True
        self._task   = asyncio.create_task(self._run())
        logger.info("TwinEventConsumer started",
                    extra={"channels": self.config.INPUT_CHANNELS})

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass

    async def _run(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self.config.INPUT_CHANNELS)
        async for msg in pubsub.listen():
            if not self.running:
                break
            if msg["type"] != "message":
                continue
            channel = msg["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()
            try:
                payload = json.loads(msg["data"])
            except (json.JSONDecodeError, TypeError):
                continue

            trace_id = payload.get("trace_id") or generate_trace_id()
            set_trace_id(trace_id)
            try:
                await self._route(channel, payload)
            except Exception as e:
                logger.error("Event consumer error",
                             extra={"channel": channel, "error": str(e)},
                             exc_info=True)
            finally:
                set_trace_id(None)

    async def _route(self, channel: str, payload: Dict[str, Any]):
        user_id = payload.get("user_id", "unknown")
        await self.graph.ensure_user(user_id)

        if channel == "neurotwin:behavior":
            await self._on_behavior(user_id, payload)
        elif channel == "neurotwin:emotion":
            await self._on_emotion(user_id, payload)
        elif channel == "neurotwin:feedback":
            await self._on_feedback(user_id, payload)
        elif channel == "neurotwin:suggestions":
            await self._on_suggestion(user_id, payload)
        elif channel == "neurotwin:twin_update":
            await self._on_twin_update(user_id, payload)

    async def _on_behavior(self, user_id: str, payload: Dict[str, Any]):
        if "pattern" in payload:
            pat = payload["pattern"]
            await self.graph.upsert_pattern(
                user_id,
                pat.get("type", "general"),
                float(pat.get("confidence", 0.5)),
                int(pat.get("evidence_count", 1)),
                pat.get("metadata", {}),
            )
            patterns = await self.graph.get_patterns(user_id)
            await self.synthesizer.synthesize(user_id, patterns)
        await self.timeline.record(user_id, TimelineEventType.PATTERN_FORMED, payload)

    async def _on_emotion(self, user_id: str, payload: Dict[str, Any]):
        emotion    = payload.get("emotion", "neutral")
        intensity  = float(payload.get("intensity", 0.5))
        if intensity >= 0.7:
            await self.timeline.record(user_id, TimelineEventType.EMOTION_SPIKE, payload)

    async def _on_feedback(self, user_id: str, payload: Dict[str, Any]):
        accepted = payload.get("accepted", False)
        await self.personality.boost_from_feedback(user_id, accepted)
        await self.timeline.record(user_id, TimelineEventType.FEEDBACK_GIVEN, payload)

    async def _on_suggestion(self, user_id: str, payload: Dict[str, Any]):
        data = payload.get("data", payload)
        await self.timeline.record(user_id, TimelineEventType.PREDICTION_MADE, data)

    async def _on_twin_update(self, user_id: str, payload: Dict[str, Any]):
        """Manual full sync trigger from cognition or orchestrator."""
        state = payload.get("cognitive_state", {})
        if state:
            await self.graph.upsert_state(user_id, state)
            await self.personality.update_from_state(user_id, state)
            await self.timeline.record(user_id, TimelineEventType.STATE_CHANGE, state)
        await self.timeline.record(user_id, TimelineEventType.TWIN_SYNC, {"source": "manual"})
