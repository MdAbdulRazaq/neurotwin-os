"""
Decision Engine - Determines whether to emit a suggestion.
Factors: fatigue, recent suggestions, acceptance rate, emotional state, interruption risk.
Phase 3: all decisions logged with trace_id. No blocking calls.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .state import CognitiveState, UserStats
from .state_model import CognitiveStateModel
from .logging_utils import get_trace_id

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """Result of a suggestion decision."""
    decision: str  # "allow" | "suppress" | "delay"
    reason: str
    delay_seconds: Optional[int] = None
    confidence_penalty: float = 0.0  # Reduction applied to suggestion confidence


class DecisionEngine:
    """
    Makes decisions about whether to emit suggestions.
    Uses multiple factors to avoid spamming and time suggestions appropriately.
    """

    # Thresholds (can be overridden via constructor)
    FATIGUE_SUPPRESS_THRESHOLD = 0.8
    ACCEPTANCE_RATE_SUPPRESS_THRESHOLD = 0.25  # Below 25% acceptance → suppress
    FOCUS_DELAY_THRESHOLD = 0.3  # Below 30% focus → delay
    MIN_MOTIVATION_FOR_WARNING = 0.4  # Don't send warnings if motivation too low
    RECENT_SUGGESTIONS_SUPPRESS = 3  # Max in last minute before suppressing

    # Delay durations
    FOCUS_DELAY_SECONDS = 60
    EMOTION_DELAY_SECONDS = 120
    COOLDOWN_AFTER_SUGGESTION = 90  # Seconds between same type

    # Emotions that cause delay
    DELAY_EMOTIONS = {"frustrated", "stressed", "angry", "overwhelmed", "anxious"}

    def __init__(self, state_model: CognitiveStateModel, state_store=None, max_suggestions_per_minute: int = 5):
        self.state_model = state_model
        self.state_store = state_store
        self.MAX_SUGGESTIONS_PER_MINUTE = max_suggestions_per_minute

    async def should_emit_suggestion(
        self,
        user_id: str,
        pattern_confidence: float,
        suggestion_type: str,
        cognitive_state: CognitiveState,
        user_stats: Optional[UserStats] = None,
        context: Optional[Dict] = None,
        strategy: str = "nudge"
    ) -> DecisionResult:
        """
        Evaluate whether to emit a suggestion.

        Args:
            user_id: User identifier
            pattern_confidence: Confidence in this pattern (0-1)
            suggestion_type: Type of pattern (routine, emotional_drift, etc.)
            cognitive_state: Current cognitive state
            user_stats: Optional user statistics
            context: Optional additional context (current_emotion, etc.)
            strategy: Suggestion strategy type

        Returns:
            DecisionResult with decision, reason, and optional delay
        """
        trace_id = get_trace_id() or "unknown"
        context = context or {}

        # Check 1: Pattern confidence threshold
        if pattern_confidence < 0.4:
            return DecisionResult(
                decision="suppress",
                reason=f"Pattern confidence too low: {pattern_confidence:.2f} < 0.4"
            )

        # Check 2: Fatigue suppression
        if cognitive_state.fatigue > self.FATIGUE_SUPPRESS_THRESHOLD:
            logger.debug("Suppressed due to fatigue", fatigue=cognitive_state.fatigue,
                        threshold=self.FATIGUE_SUPPRESS_THRESHOLD, trace_id=trace_id)
            return DecisionResult(
                decision="suppress",
                reason=f"User fatigued: {cognitive_state.fatigue:.2f} > {self.FATIGUE_SUPPRESS_THRESHOLD}"
            )

        # Check 3: Rate limiting (suggestions per minute)
        if self.state_store:
            recent_count = await self.state_store.get_suggestions_last_minute(user_id)
            if recent_count >= self.MAX_SUGGESTIONS_PER_MINUTE:
                logger.debug("Suppressed due to rate limit", recent=recent_count,
                            max_per_minute=self.MAX_SUGGESTIONS_PER_MINUTE, trace_id=trace_id)
                return DecisionResult(
                    decision="suppress",
                    reason=f"Rate limit: {recent_count} suggestions in last minute"
                )

        # Check 4: User acceptance rate
        if user_stats and user_stats.acceptance_rate < self.ACCEPTANCE_RATE_SUPPRESS_THRESHOLD:
            if user_stats.total_suggestions >= 10:  # Only after enough data
                logger.debug("Suppressed due to low acceptance",
                            acceptance_rate=user_stats.acceptance_rate,
                            threshold=self.ACCEPTANCE_RATE_SUPPRESS_THRESHOLD,
                            trace_id=trace_id)
                return DecisionResult(
                    decision="suppress",
                    reason=f"Low acceptance rate: {user_stats.acceptance_rate:.1%} < {self.ACCEPTANCE_RATE_SUPPRESS_THRESHOLD:.0%}"
                )

        # Check 5: Focus level - potential delay
        if cognitive_state.focus_level < self.FOCUS_DELAY_THRESHOLD:
            logger.debug("Delayed due to low focus", focus=cognitive_state.focus_level,
                        trace_id=trace_id)
            return DecisionResult(
                decision="delay",
                reason=f"Low focus level: {cognitive_state.focus_level:.2f} < {self.FOCUS_DELAY_THRESHOLD}",
                delay_seconds=self.FOCUS_DELAY_SECONDS
            )

        # Check 6: Emotional state delay
        current_emotion = context.get("current_emotion", "")
        if current_emotion in self.DELAY_EMOTIONS:
            logger.debug("Delayed due to emotion", emotion=current_emotion, trace_id=trace_id)
            return DecisionResult(
                decision="delay",
                reason=f"Emotional state '{current_emotion}' suggests poor timing",
                delay_seconds=self.EMOTION_DELAY_SECONDS
            )

        # Check 7: Warning strategy requires certain motivation
        if suggestion_type == "behavioral_loop" and strategy == "warning":
            if cognitive_state.motivation < self.MIN_MOTIVATION_FOR_WARNING:
                logger.debug("Warning suppressed due to low motivation",
                            motivation=cognitive_state.motivation,
                            threshold=self.MIN_MOTIVATION_FOR_WARNING,
                            trace_id=trace_id)
                return DecisionResult(
                    decision="suppress",
                    reason=f"Low motivation ({cognitive_state.motivation:.2f}) - using nudge instead of warning",
                    confidence_penalty=0.2
                )

        # Check 8: Cooldown between suggestions (if store available)
        if self.state_store and user_stats:
            last_time = user_stats.last_suggestion_time
            if last_time:
                last_ts = datetime.fromisoformat(last_time.rstrip("Z")).replace(
                    tzinfo=timezone.utc
                ).timestamp()
                elapsed = datetime.now(timezone.utc).timestamp() - last_ts
                if elapsed < self.COOLDOWN_AFTER_SUGGESTION:
                    logger.debug("Cooldown period active", elapsed=elapsed,
                                required=self.COOLDOWN_AFTER_SUGGESTION, trace_id=trace_id)
                    return DecisionResult(
                        decision="delay",
                        reason=f"Cooldown period: {int(self.COOLDOWN_AFTER_SUGGESTION - elapsed)}s remaining",
                        delay_seconds=int(self.COOLDOWN_AFTER_SUGGESTION - elapsed)
                    )

        # All checks passed
        logger.debug("Suggestion allowed", user_id=user_id, pattern_confidence=pattern_confidence,
                    suggestion_type=suggestion_type, trace_id=trace_id)
        return DecisionResult(
            decision="allow",
            reason="All decision factors evaluated positively"
        )

    async def calculate_confidence_adjustment(
        self,
        user_id: str,
        user_stats: Optional[UserStats],
        pattern: any,  # Pattern object
        suggestion_type: str
    ) -> float:
        """
        Calculate confidence adjustment based on learning factors.

        Returns:
            Adjustment factor to subtract from base confidence (0-1)
        """
        adjustment = 0.0

        # Penalty if user generally ignores suggestions
        if user_stats and user_stats.total_suggestions >= 10:
            if user_stats.acceptance_rate < 0.3:
                adjustment += 0.3
            elif user_stats.acceptance_rate < 0.5:
                adjustment += 0.15

        # Penalty if this pattern type is often rejected
        type_stats = user_stats.suggestions_by_type.get(suggestion_type, 0) if user_stats else 0
        if type_stats > 5:
            # Could calculate type-specific acceptance rate from feedback store
            # For now, simple heuristic
            pass

        # Boost if user is motivated and focused
        # (handled in suggestions.py with cognitive state)

        return min(0.5, adjustment)  # Cap at 0.5 penalty