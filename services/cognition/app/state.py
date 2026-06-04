"""
NEUROTWIN Cognition Engine — Persistent Memory Store (Phase 3)
Redis-backed state for patterns, suggestions, feedback, learning, and cognitive state.
All ops async, no blocking calls, trace_id propagated everywhere.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from .logging_utils import generate_trace_id, get_trace_id

logger = logging.getLogger(__name__)

# ── Redis key patterns ────────────────────────────────────────────────────────
KEY_PATTERNS           = "cognition:{user_id}:patterns"
KEY_SUGGESTIONS        = "cognition:{user_id}:suggestions"
KEY_FEEDBACK           = "cognition:{user_id}:feedback"
KEY_STATE              = "cognition:{user_id}:state"
KEY_STATS              = "cognition:{user_id}:stats"
KEY_ACTIVE_USERS       = "cognition:active_users"
KEY_PATTERN_TYPE_STATS = "cognition:{user_id}:pattern_type_stats:{pattern_type}"
KEY_SUGGESTION_WINDOW  = "cognition:{user_id}:suggestions_window"

DECAY_RATES = {
    "routine":           0.0001,
    "emotional_drift":   0.001,
    "behavioral_loop":   0.0005,
    "intent_prediction": 0.002,
}


class SuggestionStatus(str, Enum):
    EMITTED  = "emitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED  = "expired"


class Pattern(BaseModel):
    pattern_id:     str
    user_id:        str
    pattern_type:   str
    confidence:     float = Field(ge=0.0, le=1.0)
    evidence_count: int = 1
    first_seen:     str
    last_updated:   str
    decay_rate:     float = 0.001
    metadata:       Dict[str, Any] = {}
    last_emitted:   Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pattern":
        return cls(**data)

    def apply_decay(self, hours_elapsed: float) -> None:
        if hours_elapsed > 0:
            self.confidence = max(
                0.0, self.confidence * ((1 - self.decay_rate) ** hours_elapsed)
            )


class Suggestion(BaseModel):
    suggestion_id:   str
    user_id:         str
    pattern_id:      str
    pattern_type:    str
    text:            str
    strategy:        str
    base_confidence: float = Field(ge=0.0, le=1.0)
    adaptive_score:  float = Field(ge=0.0, le=1.0)
    reasoning:       str
    trace_id:        str
    timestamp:       str
    status:          str = SuggestionStatus.EMITTED
    cognitive_state: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Suggestion":
        return cls(**data)


class UserStats(BaseModel):
    user_id:                 str
    total_suggestions:       int   = 0
    accepted:                int   = 0
    rejected:                int   = 0
    acceptance_rate:         float = 0.0
    last_suggestion_time:    Optional[str] = None
    suggestions_last_minute: int   = 0
    suggestions_by_type:     Dict[str, int]   = {}
    average_confidence:      float = 0.0
    last_updated:            Optional[str] = None

    def record_suggestion(self, accepted: Optional[bool] = None) -> None:
        self.total_suggestions += 1
        if accepted is True:
            self.accepted += 1
        elif accepted is False:
            self.rejected += 1
        self.acceptance_rate = self.accepted / max(1, self.total_suggestions)
        self.last_suggestion_time = datetime.now(timezone.utc).isoformat()

    def update_confidence_avg(self, new_confidence: float) -> None:
        if self.total_suggestions > 0:
            self.average_confidence = (
                (self.average_confidence * (self.total_suggestions - 1) + new_confidence)
                / self.total_suggestions
            )
        else:
            self.average_confidence = new_confidence


class CognitiveState(BaseModel):
    user_id:            str
    focus_level:        float = Field(default=0.5, ge=0.0, le=1.0)
    fatigue:            float = Field(default=0.2, ge=0.0, le=1.0)
    motivation:         float = Field(default=0.6, ge=0.0, le=1.0)
    consistency_score:  float = Field(default=0.5, ge=0.0, le=1.0)
    last_updated:       Optional[str] = None

    def to_dict(self) -> Dict[str, float]:
        return {
            "focus_level":       self.focus_level,
            "fatigue":           self.fatigue,
            "motivation":        self.motivation,
            "consistency_score": self.consistency_score,
        }



# ── CognitionState — Full Redis Persistence Layer ─────────────────────────────

class CognitionState:
    """
    Redis-backed persistence for all cognition data.
    Manages: patterns, suggestions, feedback, user stats, cognitive state, active users.
    All methods are async. No blocking calls. trace_id propagated.
    """

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    # ── Active Users ──────────────────────────────────────────────────────────

    async def mark_user_active(self, user_id: str, ttl_seconds: int = 3600) -> None:
        """Mark user as active with TTL expiry."""
        score = datetime.now(timezone.utc).timestamp()
        await self.redis.zadd(KEY_ACTIVE_USERS, {user_id: score})
        # TTL managed by periodic cleanup; also set per-user marker
        await self.redis.setex(f"cognition:{user_id}:active", ttl_seconds, "1")

    async def get_active_users(self) -> List[str]:
        """Return list of currently active user IDs."""
        cutoff = datetime.now(timezone.utc).timestamp() - 3600
        await self.redis.zremrangebyscore(KEY_ACTIVE_USERS, "-inf", cutoff)
        return await self.redis.zrange(KEY_ACTIVE_USERS, 0, -1)

    async def cleanup_stale_users(self) -> None:
        """Remove users who have been inactive for >1 hour."""
        cutoff = datetime.now(timezone.utc).timestamp() - 3600
        await self.redis.zremrangebyscore(KEY_ACTIVE_USERS, "-inf", cutoff)

    # ── Patterns ──────────────────────────────────────────────────────────────

    async def save_pattern(self, user_id: str, pattern_type: str,
                           confidence: float, metadata: Dict[str, Any]) -> Pattern:
        """Save or update a pattern. Accumulates evidence if pattern_type exists."""
        key = KEY_PATTERNS.format(user_id=user_id)
        now = datetime.now(timezone.utc).isoformat()
        existing_raw = await self.redis.hget(key, pattern_type)

        if existing_raw:
            p = Pattern.from_dict(json.loads(existing_raw))
            p.evidence_count += 1
            p.confidence = min(1.0, confidence)
            p.last_updated = now
            p.metadata.update(metadata)
        else:
            p = Pattern(
                pattern_id=f"pat:{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                pattern_type=pattern_type,
                confidence=confidence,
                evidence_count=1,
                first_seen=now,
                last_updated=now,
                decay_rate=DECAY_RATES.get(pattern_type, 0.001),
                metadata=metadata,
            )

        await self.redis.hset(key, pattern_type, json.dumps(p.to_dict()))
        await self.redis.expire(key, 86400 * 7)  # 7-day TTL
        logger.debug("Pattern saved", user_id=user_id, pattern_type=pattern_type,
                     evidence=p.evidence_count, confidence=p.confidence)
        return p

    async def get_patterns(self, user_id: str) -> List[Pattern]:
        """Retrieve all patterns for a user."""
        key = KEY_PATTERNS.format(user_id=user_id)
        raw = await self.redis.hgetall(key)
        patterns = []
        for _, v in raw.items():
            try:
                patterns.append(Pattern.from_dict(json.loads(v)))
            except Exception as e:
                logger.warning("Failed to parse pattern", error=str(e))
        return patterns

    async def mark_pattern_emitted(self, user_id: str, pattern_id: str) -> None:
        """Record that a pattern was just emitted as a suggestion."""
        key = KEY_PATTERNS.format(user_id=user_id)
        now = datetime.now(timezone.utc).isoformat()
        raw = await self.redis.hgetall(key)
        for field, v in raw.items():
            try:
                p = Pattern.from_dict(json.loads(v))
                if p.pattern_id == pattern_id:
                    p.last_emitted = now
                    await self.redis.hset(key, field, json.dumps(p.to_dict()))
                    break
            except Exception:
                continue

    async def decay_patterns(self, user_id: str) -> None:
        """Apply time-based decay to all patterns for a user."""
        key = KEY_PATTERNS.format(user_id=user_id)
        raw = await self.redis.hgetall(key)
        now = datetime.now(timezone.utc)
        for field, v in raw.items():
            try:
                p = Pattern.from_dict(json.loads(v))
                last = datetime.fromisoformat(p.last_updated.rstrip("Z"))
                hours = (now - last).total_seconds() / 3600.0
                p.apply_decay(hours)
                await self.redis.hset(key, field, json.dumps(p.to_dict()))
            except Exception as e:
                logger.warning("Decay failed for pattern", error=str(e))


    # ── Suggestions ───────────────────────────────────────────────────────────

    async def record_suggestion(self, user_id: str, suggestion: Any) -> None:
        """Persist a generated suggestion to Redis history."""
        key = KEY_SUGGESTIONS.format(user_id=user_id)
        entry = {
            "suggestion_id": suggestion.suggestion_id,
            "user_id":       user_id,
            "pattern_id":    suggestion.pattern_id,
            "pattern_type":  suggestion.pattern_type,
            "text":          suggestion.text,
            "strategy":      suggestion.strategy,
            "base_confidence": suggestion.base_confidence,
            "adaptive_score":  suggestion.adaptive_score,
            "reasoning":     suggestion.reasoning,
            "trace_id":      suggestion.trace_id,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "status":        SuggestionStatus.EMITTED,
            "cognitive_state": suggestion.cognitive_state,
        }
        await self.redis.lpush(key, json.dumps(entry))
        await self.redis.ltrim(key, 0, 199)      # keep last 200
        await self.redis.expire(key, 86400 * 30) # 30-day TTL

    async def increment_suggestion_count(self, user_id: str) -> None:
        """Increment rolling 60-second suggestion window counter."""
        win_key = KEY_SUGGESTION_WINDOW.format(user_id=user_id)
        now_ts  = datetime.now(timezone.utc).timestamp()
        await self.redis.zadd(win_key, {str(now_ts): now_ts})
        cutoff  = now_ts - 60
        await self.redis.zremrangebyscore(win_key, "-inf", cutoff)
        await self.redis.expire(win_key, 120)

    async def get_suggestions_last_minute(self, user_id: str) -> int:
        """Return number of suggestions emitted in the last 60 seconds."""
        win_key = KEY_SUGGESTION_WINDOW.format(user_id=user_id)
        cutoff  = datetime.now(timezone.utc).timestamp() - 60
        await self.redis.zremrangebyscore(win_key, "-inf", cutoff)
        return await self.redis.zcard(win_key)

    # ── Feedback ──────────────────────────────────────────────────────────────

    async def record_feedback(self, user_id: str,
                              suggestion_id: str, accepted: bool) -> None:
        """Store feedback event and update suggestion status."""
        key = KEY_FEEDBACK.format(user_id=user_id)
        entry = {
            "suggestion_id": suggestion_id,
            "accepted":      accepted,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "trace_id":      get_trace_id() or generate_trace_id(),
        }
        await self.redis.lpush(key, json.dumps(entry))
        await self.redis.ltrim(key, 0, 499)      # keep last 500
        await self.redis.expire(key, 86400 * 90) # 90-day TTL

        # Update suggestion status in history
        sug_key  = KEY_SUGGESTIONS.format(user_id=user_id)
        raw_list = await self.redis.lrange(sug_key, 0, 49)  # search last 50
        for i, raw in enumerate(raw_list):
            try:
                s = json.loads(raw)
                if s.get("suggestion_id") == suggestion_id:
                    s["status"] = (
                        SuggestionStatus.ACCEPTED if accepted
                        else SuggestionStatus.REJECTED
                    )
                    await self.redis.lset(sug_key, i, json.dumps(s))
                    break
            except Exception:
                continue

    async def get_feedback_history(self, user_id: str,
                                   limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent feedback history."""
        key = KEY_FEEDBACK.format(user_id=user_id)
        raw = await self.redis.lrange(key, 0, limit - 1)
        out = []
        for r in raw:
            try:
                out.append(json.loads(r))
            except Exception:
                continue
        return out


    # ── User Stats ────────────────────────────────────────────────────────────

    async def get_user_stats(self, user_id: str) -> UserStats:
        """Load or initialise user statistics."""
        key  = KEY_STATS.format(user_id=user_id)
        raw  = await self.redis.get(key)
        if raw:
            try:
                return UserStats(**json.loads(raw))
            except Exception:
                pass
        return UserStats(user_id=user_id)

    async def update_user_stats(self, user_id: str,
                                accepted: Optional[bool] = None) -> UserStats:
        """Update acceptance counters and persist."""
        stats = await self.get_user_stats(user_id)
        stats.record_suggestion(accepted)
        stats.last_updated = datetime.now(timezone.utc).isoformat()
        key = KEY_STATS.format(user_id=user_id)
        await self.redis.setex(key, 86400 * 30, json.dumps(stats.dict()))
        return stats

    # ── Cognitive State ───────────────────────────────────────────────────────

    async def get_user_state(self, user_id: str) -> CognitiveState:
        """Load or initialise cognitive state."""
        key = KEY_STATE.format(user_id=user_id)
        raw = await self.redis.get(key)
        if raw:
            try:
                data = json.loads(raw)
                data["user_id"] = user_id
                return CognitiveState(**data)
            except Exception:
                pass
        state = CognitiveState(
            user_id=user_id,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        await self._persist_state(user_id, state)
        return state

    async def update_user_state(self, user_id: str,
                                updates: Dict[str, float]) -> None:
        """Apply partial updates to cognitive state and persist."""
        state = await self.get_user_state(user_id)
        for field, value in updates.items():
            if hasattr(state, field):
                clamped = max(0.0, min(1.0, float(value)))
                setattr(state, field, clamped)
        state.last_updated = datetime.now(timezone.utc).isoformat()
        await self._persist_state(user_id, state)

    async def _persist_state(self, user_id: str, state: CognitiveState) -> None:
        key  = KEY_STATE.format(user_id=user_id)
        data = state.to_dict()
        data["last_updated"] = state.last_updated
        await self.redis.setex(key, 86400 * 7, json.dumps(data))

    # ── Pattern-type acceptance stats ─────────────────────────────────────────

    async def get_pattern_type_stats(self, user_id: str,
                                     pattern_type: str) -> Dict[str, Any]:
        """Return acceptance stats for a specific pattern type."""
        key = KEY_PATTERN_TYPE_STATS.format(
            user_id=user_id, pattern_type=pattern_type
        )
        raw = await self.redis.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return {"total": 0, "accepted": 0, "acceptance_rate": 0.5}

    async def update_pattern_type_stats(self, user_id: str, pattern_type: str,
                                        accepted: bool) -> None:
        """Update pattern-type-specific acceptance stats."""
        key   = KEY_PATTERN_TYPE_STATS.format(
            user_id=user_id, pattern_type=pattern_type
        )
        stats = await self.get_pattern_type_stats(user_id, pattern_type)
        stats["total"] += 1
        if accepted:
            stats["accepted"] += 1
        stats["acceptance_rate"] = stats["accepted"] / max(1, stats["total"])
        await self.redis.setex(key, 86400 * 30, json.dumps(stats))

