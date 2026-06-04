"""
NEUROTWIN Cognition Engine — Phase 3: Self-Learning Autonomous Cognition
Runs continuously: listens for events, evaluates active users, emits adaptive suggestions.
Maintains trace_id throughout. No blocking calls.
"""

import asyncio
import json
import logging
import weakref
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
import redis.asyncio as aioredis

from .config import Settings
from .feedback_consumer import FeedbackConsumer
from .logging_utils import (
    generate_trace_id, get_trace_id, set_trace_id,
    setup_logging,
)
from .state import CognitionState, Pattern
from .state_model import CognitiveStateModel
from .decision import DecisionEngine, DecisionResult
from .suggestions import SuggestionGenerator, GeneratedSuggestion

logger = logging.getLogger(__name__)

# Simple LRU-like persona cache (dict with max-size eviction)
class _PersonaCache:
    def __init__(self, maxsize: int = 100):
        self._data: Dict[str, dict] = {}
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[dict]:
        return self._data.get(key)

    def set(self, key: str, value: dict) -> None:
        if len(self._data) >= self._maxsize:
            # Evict oldest entry
            oldest = next(iter(self._data))
            del self._data[oldest]
        self._data[key] = value


class CognitionEngine:
    """
    Main cognition engine: pattern evaluation → decision → adaptive suggestion → Redis publish.
    Phase 3: persistent memory, feedback loop, decision engine, cognitive state, persona evolution.
    """

    def __init__(self, config: Settings):
        self.config = config
        self.redis: Optional[aioredis.Redis] = None
        self.state_store: Optional[CognitionState] = None
        self.state_model: Optional[CognitiveStateModel] = None
        self.decision_engine: Optional[DecisionEngine] = None
        self.suggestion_gen: Optional[SuggestionGenerator] = None
        self.feedback_consumer: Optional[FeedbackConsumer] = None
        self.running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._persona_cache = _PersonaCache(maxsize=100)


    async def start(self):
        """Initialize and start the engine."""
        setup_logging("cognition")
        logger.info("Starting Cognition Engine", extra={"version": "phase-3"})

        self.redis = await aioredis.from_url(
            self.config.REDIS_URL, decode_responses=True
        )
        logger.info("Connected to Redis")

        self.state_store    = CognitionState(self.redis)
        self.state_model    = CognitiveStateModel(self.state_store)
        self.decision_engine = DecisionEngine(
            self.state_model, self.state_store,
            max_suggestions_per_minute=self.config.MAX_SUGGESTIONS_PER_MINUTE,
        )
        self.suggestion_gen = SuggestionGenerator(self.state_store, self.state_model)

        self.feedback_consumer = FeedbackConsumer(
            self.redis, self.state_store, self.state_model, self.config
        )
        await self.feedback_consumer.start()

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.PERSONA_TIMEOUT_SECONDS)
        )
        self.running = True
        logger.info("Cognition Engine started")

    async def stop(self):
        """Gracefully stop the engine."""
        self.running = False
        if self.feedback_consumer:
            await self.feedback_consumer.stop()
        if self._session:
            await self._session.close()
        if self.redis:
            await self.redis.close()
        logger.info("Cognition Engine stopped")

    async def run(self):
        """Main event loop."""
        logger.info("Entering main loop")
        while self.running:
            try:
                await self.cognition_cycle()
                await asyncio.sleep(self.config.COGNITION_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cognition cycle failed", extra={"error": str(e)}, exc_info=True)
                await asyncio.sleep(self.config.COGNITION_INTERVAL)

    async def cognition_cycle(self):
        """One full iteration of the cognition loop."""
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        try:
            await self.state_store.cleanup_stale_users()
            active_users = await self.state_store.get_active_users()

            # Decay patterns for a sample of users
            for user_id in active_users[:10]:
                try:
                    await self.state_store.decay_patterns(user_id)
                except Exception as e:
                    logger.error("Pattern decay failed", extra={"user_id": user_id, "error": str(e)})

            for user_id in active_users:
                try:
                    await self.process_user(user_id)
                except Exception as e:
                    logger.error("Failed to process user",
                                 extra={"user_id": user_id, "error": str(e)}, exc_info=True)

            logger.debug("Cognition cycle done",
                         extra={"active_users": len(active_users), "trace_id": trace_id})
        finally:
            set_trace_id(None)


    async def process_user(self, user_id: str):
        """Process cognition for a single user — full Phase 3 pipeline."""
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        try:
            cognitive_state = await self.state_model.get_state(user_id)
            user_stats      = await self.state_store.get_user_stats(user_id)
            patterns        = await self.state_store.get_patterns(user_id)
            persona         = await self._fetch_persona_with_timeout(user_id)

            context = {
                "current_emotion": await self._get_current_emotion(user_id),
                "fatigue_level":   cognitive_state.fatigue,
            }

            for pattern in patterns:
                if pattern.confidence < self.config.PATTERN_CONFIDENCE_THRESHOLD:
                    continue

                decision = await self.decision_engine.should_emit_suggestion(
                    user_id=user_id,
                    pattern_confidence=pattern.confidence,
                    suggestion_type=pattern.pattern_type,
                    cognitive_state=cognitive_state,
                    user_stats=user_stats if user_stats.total_suggestions > 0 else None,
                    context=context,
                )

                if decision.decision == "allow":
                    suggestion = await self.suggestion_gen.generate(
                        user_id=user_id,
                        pattern=pattern,
                        persona=persona,
                        cognitive_state=cognitive_state.to_dict(),
                        trace_id=trace_id,
                    )
                    if decision.confidence_penalty > 0:
                        suggestion.adaptive_score = max(
                            0.0, suggestion.adaptive_score - decision.confidence_penalty
                        )

                    await self.state_store.record_suggestion(user_id, suggestion)
                    await self.state_store.mark_pattern_emitted(user_id, pattern.pattern_id)
                    await self.state_store.increment_suggestion_count(user_id)
                    await self._publish_suggestion(suggestion)

                    logger.info("Suggestion emitted",
                                extra={
                                    "user_id": user_id,
                                    "suggestion_id": suggestion.suggestion_id,
                                    "pattern_type": pattern.pattern_type,
                                    "strategy": suggestion.strategy,
                                    "adaptive_score": suggestion.adaptive_score,
                                    "trace_id": trace_id,
                                })

                elif decision.decision == "delay":
                    logger.debug("Suggestion delayed",
                                 extra={
                                     "user_id": user_id,
                                     "pattern_type": pattern.pattern_type,
                                     "reason": decision.reason,
                                     "trace_id": trace_id,
                                 })
            # ── Digital Twin integration: push cognitive state update ────────
            try:
                state_dict = cognitive_state.to_dict()
                twin_payload = json.dumps({
                    "user_id":         user_id,
                    "cognitive_state": state_dict,
                    "trace_id":        trace_id,
                    "source":          "cognition",
                    "timestamp":       datetime.now(timezone.utc).isoformat(),
                })
                await self.redis.publish("neurotwin:twin_update", twin_payload)
                logger.debug("Twin update published",
                             extra={"user_id": user_id, "trace_id": trace_id})
            except Exception as tw_err:
                logger.warning("Twin update publish failed",
                               extra={"user_id": user_id, "error": str(tw_err)})
        finally:
            set_trace_id(None)

    async def _fetch_persona_with_timeout(self, user_id: str) -> Optional[Dict]:
        """Fetch user persona from agents service with 500ms timeout. Falls back to default."""
        cached = self._persona_cache.get(user_id)
        if cached:
            return cached
        if not self.config.PERSONA_AGENT_URL:
            return self._default_persona()
        try:
            async with self._session.get(
                f"{self.config.PERSONA_AGENT_URL}/persona/{user_id}",
                timeout=aiohttp.ClientTimeout(total=0.5),
            ) as resp:
                if resp.status == 200:
                    persona = await resp.json()
                    self._persona_cache.set(user_id, persona)
                    return persona
        except asyncio.TimeoutError:
            logger.warning("Persona fetch timeout (500ms)", extra={"user_id": user_id})
        except Exception as e:
            logger.error("Persona fetch error", extra={"user_id": user_id, "error": str(e)})
        return self._default_persona()

    def _default_persona(self) -> Dict:
        return {"tone": "neutral", "formality": "standard", "emoji_usage": "none", "name": "NeuroTwin"}

    async def _get_current_emotion(self, user_id: str) -> str:
        try:
            raw = await self.redis.get(f"emotion:{user_id}:current")
            if raw:
                data = json.loads(raw)
                return data.get("emotion", "")
        except Exception:
            pass
        return ""

    async def _publish_suggestion(self, suggestion: GeneratedSuggestion):
        """Publish fully-formed suggestion to Redis output channel."""
        payload = {
            "trace_id": suggestion.trace_id,
            "user_id":  suggestion.user_id,
            "data": {
                "suggestion_id": suggestion.suggestion_id,
                "suggestion":    suggestion.text,
                "type":          suggestion.pattern_type,
                "strategy":      suggestion.strategy,
                "confidence":    suggestion.base_confidence,
                "adaptive_score": suggestion.adaptive_score,
                "reasoning":     suggestion.reasoning,
                "cognitive_state": suggestion.cognitive_state,
                "timestamp":     datetime.now(timezone.utc).isoformat(),
            },
        }
        await self.redis.publish("neurotwin:suggestions", json.dumps(payload))
        logger.info("Suggestion published",
                    extra={"suggestion_id": suggestion.suggestion_id,
                           "user_id": suggestion.user_id,
                           "strategy": suggestion.strategy,
                           "trace_id": suggestion.trace_id})


async def main():
    config = Settings()
    engine = CognitionEngine(config)
    try:
        await engine.start()
        await engine.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
