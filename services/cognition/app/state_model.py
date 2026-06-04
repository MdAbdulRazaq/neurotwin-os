"""
Cognitive State Model - Dynamic state calculations based on behavior and emotion.
Tracks: focus_level, fatigue, motivation, consistency_score (all 0-1).
Phase 3: fully async, no blocking, trace_id propagated.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field

from .logging_utils import get_trace_id
from .state import CognitionState, CognitiveState

logger = logging.getLogger(__name__)


class CognitiveStateUpdate(BaseModel):
    """Request to update cognitive state components."""
    focus_delta:       Optional[float] = None
    fatigue_delta:     Optional[float] = None
    motivation_delta:  Optional[float] = None
    consistency_delta: Optional[float] = None


class StateUpdateFactors(BaseModel):
    """Factors that influence state changes."""
    event_type: str
    intensity: float = 1.0  # 0-1 scale of impact
    duration_minutes: float = 1.0
    context: Dict = {}


class CognitiveStateModel:
    """
    Models user's cognitive state dynamically.
    Updates based on behavior events, emotion data, and feedback.
    """

    # Update rates (per event)
    BASE_FATIGUE_RATE = 0.01  # Per interaction
    FATIGUE_DECAY_RATE = 0.005  # Per minute
    FOCUS_IMPROVEMENT_RATE = 0.02  # Per focused activity
    FOCUS_DECAY_RATE = 0.003  # Per minute without engagement
    MOTIVATION_BOOST_ACCEPTED = 0.08  # When suggestion accepted
    MOTIVATION_DROP_REJECTED = 0.05  # When suggestion rejected
    CONSISTENCY_INCREASE_RATE = 0.01  # Per routine pattern
    CONSISTENCY_DECAY_RATE = 0.002  # Per minute of disruption

    def __init__(self, state_store: CognitionState):
        self.state_store = state_store

    async def get_state(self, user_id: str) -> CognitiveState:
        """Get current cognitive state for user."""
        return await self.state_store.get_user_state(user_id)

    async def update_from_behavior(self, user_id: str, event_type: str,
                                   data: Dict) -> CognitiveState:
        """
        Update cognitive state based on behavior event.

        Args:
            event_type: Type of behavior (e.g., "interaction", "task_complete", "break")
            data: Additional context (duration, intensity, etc.)
        """
        trace_id = get_trace_id()
        current = await self.get_state(user_id)

        # Calculate deltas based on event type
        updates = {}

        if event_type == "interaction":
            # Each interaction adds fatigue
            intensity = data.get("intensity", 1.0)
            updates["fatigue_delta"] = self.BASE_FATIGUE_RATE * intensity
            # Focus improves with sustained interaction
            if data.get("sustained", False):
                updates["focus_delta"] = self.FOCUS_IMPROVEMENT_RATE * 0.5
            else:
                updates["focus_delta"] = -self.FOCUS_DECAY_RATE * 0.5

        elif event_type == "task_complete":
            # Task completion boosts motivation and consistency
            updates["motivation_delta"] = self.MOTIVATION_BOOST_ACCEPTED * 0.5  # Partial boost
            updates["consistency_delta"] = self.CONSISTENCY_INCREASE_RATE

        elif event_type == "break":
            # Break reduces fatigue
            duration = data.get("duration_minutes", 5)
            fatigue_recovery = min(0.5, self.FATIGUE_DECAY_RATE * duration)
            updates["fatigue_delta"] = -fatigue_recovery
            updates["focus_delta"] = self.FOCUS_IMPROVEMENT_RATE * 0.3

        elif event_type == "session_start":
            # Session start: low fatigue, high focus
            updates["focus_delta"] = 0.2
            updates["fatigue_delta"] = -0.1

        elif event_type == "session_end":
            # Session end: high fatigue, low focus
            updates["fatigue_delta"] = self.BASE_FATIGUE_RATE * 2
            updates["focus_delta"] = -0.3

        elif event_type == "intensive_use":
            # Heavy usage increases fatigue rapidly
            updates["fatigue_delta"] = self.BASE_FATIGUE_RATE * 3
            updates["focus_delta"] = -self.FOCUS_DECAY_RATE * 2
            updates["motivation_delta"] = -0.05

        # Apply updates with bounds
        for field, delta in updates.items():
            current_value = getattr(current, field.replace("_delta", ""))
            new_value = max(0.0, min(1.0, current_value + delta))
            setattr(current, field.replace("_delta", ""), new_value)

        current.last_updated = datetime.utcnow().isoformat() + "Z"

        # Persist
        await self.state_store.update_user_state(
            user_id,
            {
                "focus_level": current.focus_level,
                "fatigue": current.fatigue,
                "motivation": current.motivation,
                "consistency_score": current.consistency_score,
            }
        )

        logger.debug("State updated from behavior",
                     user_id=user_id, event_type=event_type,
                     updates=updates, trace_id=trace_id)
        return current

    async def update_from_emotion(self, user_id: str, emotion_data: Dict) -> CognitiveState:
        """
        Update cognitive state based on emotion detection.

        Args:
            emotion_data: {"emotion": "stressed", "intensity": 0.8, "duration_minutes": 5}
        """
        trace_id = get_trace_id()
        current = await self.get_state(user_id)

        emotion = emotion_data.get("emotion", "").lower()
        intensity = emotion_data.get("intensity", 1.0)

        updates = {}

        # Emotion-based updates
        if emotion in ["stressed", "frustrated", "angry"]:
            updates["fatigue_delta"] = 0.05 * intensity
            updates["focus_delta"] = -0.1 * intensity
            updates["motivation_delta"] = -0.08 * intensity

        elif emotion in ["calm", "relaxed", "content"]:
            updates["fatigue_delta"] = -0.03 * intensity
            updates["focus_delta"] = 0.05 * intensity

        elif emotion in ["excited", "engaged", "happy"]:
            updates["motivation_delta"] = 0.06 * intensity
            updates["focus_delta"] = 0.08 * intensity

        elif emotion in ["bored", "disengaged"]:
            updates["focus_delta"] = -0.1 * intensity
            updates["motivation_delta"] = -0.05 * intensity

        elif emotion in ["tired", "fatigued"]:
            updates["fatigue_delta"] = 0.1 * intensity
            updates["focus_delta"] = -0.08 * intensity

        # Apply updates
        for field, delta in updates.items():
            current_value = getattr(current, field.replace("_delta", ""))
            new_value = max(0.0, min(1.0, current_value + delta))
            setattr(current, field.replace("_delta", ""), new_value)

        current.last_updated = datetime.utcnow().isoformat() + "Z"

        await self.state_store.update_user_state(
            user_id,
            {
                "focus_level": current.focus_level,
                "fatigue": current.fatigue,
                "motivation": current.motivation,
                "consistency_score": current.consistency_score,
            }
        )

        logger.debug("State updated from emotion",
                     user_id=user_id, emotion=emotion,
                     updates=updates, trace_id=trace_id)
        return current

    async def adjust_from_feedback(self, user_id: str, accepted: bool) -> CognitiveState:
        """
        Adjust cognitive state based on suggestion feedback.

        Args:
            accepted: Whether user accepted the suggestion
        """
        trace_id = get_trace_id()
        current = await self.get_state(user_id)

        if accepted:
            # Positive reinforcement
            current.motivation = min(1.0, current.motivation + self.MOTIVATION_BOOST_ACCEPTED)
            # Focus may improve if suggestion was helpful
            current.focus_level = min(1.0, current.focus_level + 0.03)
        else:
            # Rejection can lower motivation slightly
            current.motivation = max(0.0, current.motivation - self.MOTIVATION_DROP_REJECTED)
            # Fatigue may increase if interruption
            current.fatigue = min(1.0, current.fatigue + 0.05)

        current.last_updated = datetime.utcnow().isoformat() + "Z"

        await self.state_store.update_user_state(
            user_id,
            {
                "motivation": current.motivation,
                "focus_level": current.focus_level,
                "fatigue": current.fatigue,
            }
        )

        logger.debug("State adjusted from feedback",
                     user_id=user_id, accepted=accepted,
                     new_motivation=current.motivation,
                     trace_id=trace_id)
        return current

    async def apply_natural_decay(self, user_id: str) -> CognitiveState:
        """
        Apply natural state decay over time.
        Called periodically to simulate state changes without events.
        """
        trace_id = get_trace_id()
        current = await self.get_state(user_id)

        # Check how long since last update
        last_updated = datetime.fromisoformat(current.last_updated.rstrip("Z"))
        hours_elapsed = (datetime.utcnow() - last_updated).total_seconds() / 3600

        if hours_elapsed > 0.1:  # Only apply if more than 6 minutes
            decay_factor_focus = (1 - self.FOCUS_DECAY_RATE) ** hours_elapsed
            decay_factor_fatigue = (1 + self.FATIGUE_DECAY_RATE * 0.5) ** hours_elapsed
            decay_factor_motivation = (1 - 0.003) ** hours_elapsed

            current.focus_level = max(0.2, current.focus_level * decay_factor_focus)
            current.fatigue = min(0.9, current.fatigue * decay_factor_fatigue)
            current.motivation = max(0.3, current.motivation * decay_factor_motivation)

            current.last_updated = datetime.utcnow().isoformat() + "Z"

            await self.state_store.update_user_state(
                user_id,
                {
                    "focus_level": current.focus_level,
                    "fatigue": current.fatigue,
                    "motivation": current.motivation,
                }
            )

            logger.debug("Natural decay applied",
                         user_id=user_id,
                         hours_elapsed=round(hours_elapsed, 2),
                         trace_id=trace_id)

        return current

    async def calculate_consistency(self, user_id: str, pattern_strength: float = 0.0) -> None:
        """
        Update consistency score based on pattern adherence.

        Args:
            pattern_strength: How strongly patterns are showing (0-1)
        """
        trace_id = get_trace_id()
        current = await self.get_state(user_id)

        if pattern_strength > 0.5:
            # Strong pattern adherence increases consistency
            boost = (pattern_strength - 0.5) * 0.1
            current.consistency_score = min(1.0, current.consistency_score + boost)
        else:
            # Weak patterns decrease consistency over time
            current.consistency_score = max(0.0, current.consistency_score - 0.005)

        await self.state_store.update_user_state(
            user_id,
            {"consistency_score": current.consistency_score}
        )

        logger.debug("Consistency updated",
                     user_id=user_id,
                     consistency_score=current.consistency_score,
                     trace_id=trace_id)


logger.info("CognitiveStateModel module loaded")