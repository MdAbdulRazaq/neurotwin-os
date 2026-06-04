"""
Feedback Consumer - Background process for all incoming events.
Subscribes to Redis channels and updates state, patterns, and learning.
Phase 3: trace_id on every message, all channels, no CHANNELS constant needed.
"""

import asyncio
import json
import logging
from typing import Dict

import redis.asyncio as aioredis

from .config import Settings
from .logging_utils import get_trace_id, generate_trace_id, set_trace_id
from .state import CognitionState
from .state_model import CognitiveStateModel

logger = logging.getLogger(__name__)


class FeedbackConsumer:
    """
    Background consumer that listens to multiple channels and updates cognition state.
    Also maintains active_users tracking.
    """

    def __init__(self, redis: aioredis.Redis, state_store: CognitionState,
                 state_model: CognitiveStateModel, config: Settings):
        self.redis = redis
        self.state_store = state_store
        self.state_model = state_model
        self.config = config
        self.running = False
        self._task = None

    async def start(self):
        """Start the consumer in background."""
        self.running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Feedback consumer started",
                    extra={"channels": self.config.INPUT_CHANNELS})

    async def stop(self):
        """Stop the consumer."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Feedback consumer stopped")

    async def _run(self):
        """Main consumer loop."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self.config.INPUT_CHANNELS)

        logger.info("Subscribed to channels",
                    extra={"channels": self.config.INPUT_CHANNELS})

        async for message in pubsub.listen():
            if not self.running:
                break

            if message["type"] != "message":
                continue

            channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
            data = message["data"]

            # Parse JSON data
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                payload = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in message",
                             extra={"channel": channel, "error": str(e)})
                continue

            # Extract trace_id if present (critical fix 6)
            trace_id = payload.get("trace_id") or generate_trace_id()
            set_trace_id(trace_id)

            # Process based on channel
            try:
                await self._handle_channel(channel, payload)
            except Exception as e:
                logger.error("Failed to handle message",
                             extra={"channel": channel, "error": str(e), "trace_id": trace_id},
                             exc_info=True)
            finally:
                set_trace_id(None)

    async def _handle_channel(self, channel: str, payload: Dict):
        """Route message to appropriate handler."""
        user_id = payload.get("user_id", "unknown")
        logger.debug("Processing channel message",
                     extra={"channel": channel, "user_id": user_id})

        # Mark user as active (critical fix 2)
        await self.state_store.mark_user_active(user_id, ttl_seconds=self.config.ACTIVE_USER_TTL_SECONDS)

        if channel == "neurotwin:behavior":
            await self._handle_behavior(user_id, payload)
        elif channel == "neurotwin:emotion":
            await self._handle_emotion(user_id, payload)
        elif channel == "neurotwin:voice":
            await self._handle_voice(user_id, payload)
        elif channel == "neurotwin:memory":
            await self._handle_memory(user_id, payload)
        elif channel == "neurotwin:prediction":
            await self._handle_prediction(user_id, payload)
        elif channel == "neurotwin:feedback":
            await self._handle_feedback(user_id, payload)
        else:
            logger.warning("Unknown channel", extra={"channel": channel})

    async def _handle_behavior(self, user_id: str, payload: Dict):
        """Handle behavior event."""
        event_type = payload.get("type", "interaction")
        data = payload.get("data", {})

        await self.state_model.update_from_behavior(user_id, event_type, data)

        # Save pattern if detected
        if "pattern" in payload:
            pattern_type = payload["pattern"].get("type", "general")
            confidence = payload["pattern"].get("confidence", 0.5)
            metadata = payload["pattern"].get("metadata", {})
            await self.state_store.save_pattern(user_id, pattern_type, confidence, metadata)

    async def _handle_emotion(self, user_id: str, payload: Dict):
        """Handle emotion event."""
        emotion_data = {
            "emotion": payload.get("emotion", ""),
            "intensity": payload.get("intensity", 1.0),
            "duration_minutes": payload.get("duration_minutes", 1.0),
        }
        await self.state_model.update_from_emotion(user_id, emotion_data)

    async def _handle_voice(self, user_id: str, payload: Dict):
        """Handle voice/audio event."""
        # Voice events can indicate engagement level
        voice_data = payload.get("data", {})
        if voice_data.get("speech_detected"):
            # User is speaking/engaged
            await self.state_store.update_user_state(
                user_id,
                {"focus_level": 0.1}  # Small boost
            )

    async def _handle_memory(self, user_id: str, payload: Dict):
        """Handle memory/recall event."""
        # Memory events can indicate consistency
        memory_type = payload.get("memory_type", "")
        if memory_type == "recall":
            # User recalled something - consistency boost
            await self.state_store.update_user_state(
                user_id,
                {"consistency_score": 0.02}
            )

    async def _handle_prediction(self, user_id: str, payload: Dict):
        """Handle prediction event from ML models."""
        # Predictions may contain new patterns
        if "patterns" in payload:
            for pattern in payload["patterns"]:
                await self.state_store.save_pattern(
                    user_id,
                    pattern.get("type", "intent_prediction"),
                    pattern.get("confidence", 0.5),
                    pattern.get("metadata", {})
                )

    async def _handle_feedback(self, user_id: str, payload: Dict):
        """Handle user feedback on suggestions."""
        suggestion_id = payload.get("suggestion_id")
        accepted = payload.get("accepted", False)

        if not suggestion_id:
            logger.warning("Feedback missing suggestion_id", extra={"user_id": user_id})
            return

        await self.state_store.record_feedback(user_id, suggestion_id, accepted)
        await self.state_store.update_user_stats(user_id, accepted=accepted)
        await self.state_store.update_pattern_type_stats(
            user_id,
            payload.get("pattern_type", "general"),
            accepted
        )
        await self.state_model.adjust_from_feedback(user_id, accepted)

        logger.info("Feedback processed",
                    extra={"user_id": user_id,
                           "suggestion_id": suggestion_id,
                           "accepted": accepted})


logger.info("FeedbackConsumer module loaded")