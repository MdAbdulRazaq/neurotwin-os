"""
NEUROTWIN Digital Twin — Prediction Engine (Phase 4)
Predicts next user actions from patterns, cognitive state, and timeline trends.
Uses weighted scoring over pattern types and time-of-day heuristics.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .graph import IdentityGraph
from .logging_utils import get_trace_id

logger = logging.getLogger(__name__)

# Action → pattern type affinity weights
ACTION_PATTERN_WEIGHTS: Dict[str, Dict[str, float]] = {
    "study":     {"routine": 0.4, "intent_prediction": 0.3, "learning": 0.3},
    "exercise":  {"routine": 0.5, "behavioral_loop": 0.2, "health": 0.3},
    "rest":      {"routine": 0.3, "emotional_drift": 0.4, "rest": 0.3},
    "socialize": {"routine": 0.2, "emotional_drift": 0.3, "social_energy": 0.5},
    "work":      {"routine": 0.4, "intent_prediction": 0.3, "productivity": 0.3},
    "create":    {"intent_prediction": 0.4, "learning": 0.3, "openness": 0.3},
}

# Time-of-day boosters (hour → action boosts)
TIME_BOOSTERS: Dict[int, Dict[str, float]] = {
    **{h: {"study": 0.1, "work": 0.1}    for h in range(8, 12)},
    **{h: {"rest": 0.15, "socialize": 0.1} for h in range(12, 14)},
    **{h: {"work": 0.15, "create": 0.1}  for h in range(14, 18)},
    **{h: {"exercise": 0.1, "rest": 0.1} for h in range(18, 21)},
    **{h: {"study": 0.15, "rest": 0.1}   for h in range(21, 24)},
}


class Predictor:
    """Predicts the user's next likely action within 24 hours."""

    def __init__(self, graph: IdentityGraph):
        self.graph = graph

    async def predict_next_action(
        self,
        user_id: str,
        cognitive_state: Optional[Dict[str, float]] = None,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Predict next action. Returns:
        {
          "predicted_action": str,
          "confidence": float,
          "reasoning": str,
          "alternatives": [{action, confidence}],
          "horizon_hours": int,
          "trace_id": str
        }
        """
        trace_id = get_trace_id() or ""
        cognitive_state = cognitive_state or {}
        now_hour = datetime.now(timezone.utc).hour

        # Load patterns from graph
        patterns = await self.graph.get_patterns(user_id)
        pat_map  = {p["type"]: p for p in patterns}

        # Score each candidate action
        scores: Dict[str, float] = {}
        for action, pat_weights in ACTION_PATTERN_WEIGHTS.items():
            score = 0.0
            for pat_type, weight in pat_weights.items():
                pat = pat_map.get(pat_type)
                if pat:
                    score += weight * float(pat.get("confidence", 0.0))
            # Apply time-of-day boost
            time_boost = TIME_BOOSTERS.get(now_hour, {}).get(action, 0.0)
            score += time_boost
            # Apply cognitive state modifier
            score = self._apply_state_modifier(action, score, cognitive_state)
            scores[action] = round(min(1.0, max(0.0, score)), 4)

        if not scores:
            return self._no_prediction(trace_id, horizon_hours)

        # Sort
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_action, best_conf = ranked[0]

        reasoning = self._build_reasoning(
            best_action, best_conf, pat_map, cognitive_state, now_hour
        )

        return {
            "predicted_action": best_action,
            "confidence":       best_conf,
            "reasoning":        reasoning,
            "alternatives":     [{"action": a, "confidence": c} for a, c in ranked[1:4]],
            "horizon_hours":    horizon_hours,
            "trace_id":         trace_id,
        }

    def _apply_state_modifier(self, action: str, score: float,
                               state: Dict[str, float]) -> float:
        fatigue    = state.get("fatigue", 0.2)
        motivation = state.get("motivation", 0.6)
        if action == "rest" and fatigue > 0.6:
            score *= 1.3
        if action in ("study", "work", "create") and motivation > 0.7:
            score *= 1.2
        if action in ("study", "work") and fatigue > 0.7:
            score *= 0.7
        return score

    def _build_reasoning(self, action: str, confidence: float,
                         pat_map: Dict, state: Dict, hour: int) -> str:
        parts = [f"Predicted '{action}' (conf={confidence:.2f})"]
        if action in ACTION_PATTERN_WEIGHTS:
            for pt in ACTION_PATTERN_WEIGHTS[action]:
                if pt in pat_map:
                    parts.append(
                        f"Pattern '{pt}' (conf={pat_map[pt].get('confidence',0):.2f})"
                    )
        if hour in TIME_BOOSTERS and action in TIME_BOOSTERS[hour]:
            parts.append(f"Time-of-day boost at hour {hour}")
        if state.get("fatigue", 0) > 0.6:
            parts.append("High fatigue noted")
        if state.get("motivation", 0) > 0.7:
            parts.append("High motivation noted")
        return " | ".join(parts)

    def _no_prediction(self, trace_id: str, horizon: int) -> Dict[str, Any]:
        return {
            "predicted_action": "rest",
            "confidence":       0.3,
            "reasoning":        "Insufficient pattern data — defaulting to rest",
            "alternatives":     [],
            "horizon_hours":    horizon,
            "trace_id":         trace_id,
        }
