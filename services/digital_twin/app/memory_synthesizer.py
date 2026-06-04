"""
NEUROTWIN Digital Twin — Memory Synthesizer (Phase 4)
Converts repeated patterns into stable personality traits.
Rule: pattern with evidence_count >= threshold AND confidence >= floor → becomes trait.
"""
import logging
from typing import Any, Dict, List

from .graph import IdentityGraph
from .logging_utils import get_trace_id

logger = logging.getLogger(__name__)

# Maps pattern_type → trait_name it reinforces
PATTERN_TRAIT_MAP: Dict[str, str] = {
    "routine":           "conscientiousness",
    "behavioral_loop":   "conscientiousness",
    "emotional_drift":   "stability",
    "intent_prediction": "openness",
    "learning":          "openness",
    "productivity":      "motivation_drive",
    "health":            "conscientiousness",
    "entertainment":     "social_energy",
    "rest":              "stability",
}


class MemorySynthesizer:
    """Synthesizes traits from accumulated pattern evidence."""

    def __init__(self, graph: IdentityGraph,
                 evidence_threshold: int = 3,
                 confidence_floor: float = 0.3):
        self.graph = graph
        self.evidence_threshold = evidence_threshold
        self.confidence_floor = confidence_floor

    async def synthesize(self, user_id: str,
                         patterns: List[Dict[str, Any]]) -> List[str]:
        """
        Check all patterns. For those that qualify, upsert the mapped trait.
        Returns list of trait names that were synthesized/updated.
        """
        trace_id = get_trace_id() or ""
        synthesized: List[str] = []

        for pat in patterns:
            ptype      = pat.get("type") or pat.get("pattern_type", "")
            confidence = float(pat.get("confidence", 0.0))
            evidence   = int(pat.get("evidence_count", 0))

            if evidence < self.evidence_threshold:
                continue
            if confidence < self.confidence_floor:
                continue

            trait_name = PATTERN_TRAIT_MAP.get(ptype)
            if not trait_name:
                continue

            # Trait value = scaled confidence, capped 0-1
            trait_value = round(min(1.0, confidence * 0.9 + 0.1), 4)
            await self.graph.upsert_trait(
                user_id, trait_name, trait_value, source="pattern_synthesis"
            )
            synthesized.append(trait_name)
            logger.debug("Trait synthesized from pattern",
                         extra={"user_id": user_id, "pattern": ptype,
                                "trait": trait_name, "value": trait_value,
                                "trace_id": trace_id})

        if synthesized:
            logger.info("Memory synthesis complete",
                        extra={"user_id": user_id,
                               "synthesized_traits": synthesized,
                               "trace_id": trace_id})
        return synthesized
