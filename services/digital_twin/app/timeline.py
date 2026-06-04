"""
NEUROTWIN Digital Twin — Timeline System (Phase 4)
Tracks all significant behavior changes over time in Neo4j.
Every state update, trait change, or pattern milestone is recorded.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .graph import IdentityGraph
from .logging_utils import get_trace_id

logger = logging.getLogger(__name__)

# Event types
class TimelineEventType:
    STATE_CHANGE    = "state_change"
    TRAIT_UPDATE    = "trait_update"
    PATTERN_FORMED  = "pattern_formed"
    FEEDBACK_GIVEN  = "feedback_given"
    EMOTION_SPIKE   = "emotion_spike"
    PREDICTION_MADE = "prediction_made"
    TWIN_SYNC       = "twin_sync"


class Timeline:
    """Records and retrieves the user's behavioral timeline."""

    def __init__(self, graph: IdentityGraph):
        self.graph = graph

    async def record(self, user_id: str,
                     event_type: str,
                     data: Dict[str, Any]) -> None:
        """Persist a timeline event to Neo4j."""
        trace_id = get_trace_id() or ""
        payload  = {**data, "trace_id": trace_id}
        try:
            await self.graph.add_timeline_event(user_id, event_type, payload)
            logger.debug("Timeline event recorded",
                         extra={"user_id": user_id,
                                "event_type": event_type,
                                "trace_id": trace_id})
        except Exception as e:
            logger.error("Failed to record timeline event",
                         extra={"user_id": user_id,
                                "event_type": event_type,
                                "error": str(e)})

    async def get_recent(self, user_id: str,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the most recent timeline events."""
        try:
            return await self.graph.get_timeline(user_id, limit=limit)
        except Exception as e:
            logger.error("Failed to fetch timeline",
                         extra={"user_id": user_id, "error": str(e)})
            return []

    async def get_state_delta(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Compare most recent two state_change events.
        Returns a delta dict showing how each dimension changed.
        """
        events = await self.get_recent(user_id, limit=100)
        state_events = [e for e in events
                        if e["event_type"] == TimelineEventType.STATE_CHANGE]
        if len(state_events) < 2:
            return None

        latest = state_events[0]["data"]
        prev   = state_events[1]["data"]
        delta  = {}
        for key in ["focus_level", "fatigue", "motivation", "consistency_score"]:
            if key in latest and key in prev:
                delta[key] = round(float(latest[key]) - float(prev[key]), 4)
        return delta
