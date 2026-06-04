"""
NEUROTWIN Digital Twin — Profile Generator (Phase 4)
Assembles the complete digital twin profile from all subsystems.
Cached in Redis for PROFILE_CACHE_TTL seconds.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from .graph import IdentityGraph
from .personality import PersonalityEngine
from .predictor import Predictor
from .timeline import Timeline
from .logging_utils import get_trace_id, generate_trace_id

logger = logging.getLogger(__name__)

CACHE_KEY = "digital_twin:{user_id}:profile"


class ProfileGenerator:
    """Generates and caches the full digital twin profile for a user."""

    def __init__(self, graph: IdentityGraph, personality: PersonalityEngine,
                 predictor: Predictor, timeline: Timeline,
                 redis: aioredis.Redis, cache_ttl: int = 300):
        self.graph       = graph
        self.personality = personality
        self.predictor   = predictor
        self.timeline    = timeline
        self.redis       = redis
        self.cache_ttl   = cache_ttl

    async def generate(self, user_id: str,
                       force_refresh: bool = False) -> Dict[str, Any]:
        """
        Build full profile. Uses Redis cache unless force_refresh=True.
        Profile structure:
        {
          "user_id": str,
          "trace_id": str,
          "generated_at": ISO str,
          "identity": { traits, dominant_trait },
          "patterns": [ ... ],
          "cognitive_state": { ... },
          "prediction": { ... },
          "timeline_summary": { event_count, last_event_type, state_delta },
          "twin_level": "L3" (always — we're at cognitive tier)
        }
        """
        trace_id = get_trace_id() or generate_trace_id()
        cache_key = CACHE_KEY.format(user_id=user_id)

        if not force_refresh:
            cached = await self._get_cache(cache_key)
            if cached:
                return cached

        # Gather all subsystems in parallel-style (sequential but fast)
        traits         = await self.graph.get_traits(user_id)
        patterns       = await self.graph.get_patterns(user_id)
        state          = await self.graph.get_state(user_id) or {}
        dominant_trait = await self.personality.get_dominant_trait(user_id)
        prediction     = await self.predictor.predict_next_action(
            user_id, cognitive_state=state
        )
        timeline_events = await self.timeline.get_recent(user_id, limit=20)

        # Timeline summary
        state_delta = await self.timeline.get_state_delta(user_id)
        timeline_summary = {
            "event_count":     len(timeline_events),
            "last_event_type": timeline_events[0]["event_type"] if timeline_events else None,
            "state_delta":     state_delta,
        }

        profile = {
            "user_id":        user_id,
            "trace_id":       trace_id,
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "twin_level":     "L3",
            "identity": {
                "traits":         traits,
                "dominant_trait": dominant_trait,
                "trait_count":    len(traits),
            },
            "patterns": patterns,
            "cognitive_state": state,
            "prediction":     prediction,
            "timeline_summary": timeline_summary,
        }

        await self._set_cache(cache_key, profile)
        logger.info("Profile generated",
                    extra={"user_id": user_id, "trait_count": len(traits),
                           "pattern_count": len(patterns), "trace_id": trace_id})
        return profile

    async def invalidate(self, user_id: str) -> None:
        """Invalidate the cached profile (call after any update)."""
        cache_key = CACHE_KEY.format(user_id=user_id)
        await self.redis.delete(cache_key)

    async def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = await self.redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        try:
            await self.redis.setex(key, self.cache_ttl, json.dumps(data))
        except Exception as e:
            logger.warning("Profile cache write failed", extra={"error": str(e)})
