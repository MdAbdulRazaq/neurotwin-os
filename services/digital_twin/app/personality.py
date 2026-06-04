"""
NEUROTWIN Digital Twin — Personality Engine (Phase 4)
Dynamically updates personality traits from cognitive state + feedback.
Trait model: openness, conscientiousness, stability, motivation_drive, social_energy (0-1).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .graph import IdentityGraph
from .logging_utils import get_trace_id

logger = logging.getLogger(__name__)

# Trait definitions and their cognitive-state influences
TRAIT_RULES: Dict[str, Dict[str, float]] = {
    "openness":          {"motivation": +0.3, "focus_level": +0.2, "fatigue": -0.1},
    "conscientiousness": {"consistency_score": +0.4, "focus_level": +0.3, "fatigue": -0.1},
    "stability":         {"fatigue": -0.4, "motivation": +0.2, "focus_level": +0.1},
    "motivation_drive":  {"motivation": +0.5, "focus_level": +0.2, "fatigue": -0.2},
    "social_energy":     {"motivation": +0.2, "focus_level": +0.1, "fatigue": -0.1},
}

BASE_TRAIT_VALUE = 0.5


class PersonalityEngine:
    """Computes and updates user personality traits in Neo4j."""

    def __init__(self, graph: IdentityGraph):
        self.graph = graph

    async def update_from_state(self, user_id: str,
                                cognitive_state: Dict[str, float]) -> Dict[str, float]:
        """
        Recompute all 5 traits from current cognitive state and persist to graph.
        Returns computed trait dict.
        """
        trace_id = get_trace_id() or generate_trace_id()
        traits: Dict[str, float] = {}

        for trait_name, weights in TRAIT_RULES.items():
            score = BASE_TRAIT_VALUE
            for state_key, weight in weights.items():
                state_val = cognitive_state.get(state_key, 0.5)
                score += weight * (state_val - 0.5)   # delta from baseline
            score = round(max(0.0, min(1.0, score)), 4)
            traits[trait_name] = score
            await self.graph.upsert_trait(
                user_id, trait_name, score, source="cognitive_state"
            )

        logger.info("Personality updated from state",
                    extra={"user_id": user_id, "traits": traits, "trace_id": trace_id})
        return traits

    async def boost_from_feedback(self, user_id: str, accepted: bool) -> None:
        """Nudge motivation_drive and conscientiousness based on feedback."""
        existing = await self.graph.get_traits(user_id)
        trait_map = {t["name"]: t["value"] for t in existing}

        delta = +0.02 if accepted else -0.01
        for trait_name in ["motivation_drive", "conscientiousness"]:
            old = trait_map.get(trait_name, BASE_TRAIT_VALUE)
            new = round(max(0.0, min(1.0, old + delta)), 4)
            await self.graph.upsert_trait(user_id, trait_name, new, source="feedback")

    async def get_dominant_trait(self, user_id: str) -> str:
        """Return the name of the highest-scoring trait."""
        traits = await self.graph.get_traits(user_id)
        if not traits:
            return "balanced"
        return max(traits, key=lambda t: t["value"])["name"]


def generate_trace_id() -> str:
    import uuid; return uuid.uuid4().hex
