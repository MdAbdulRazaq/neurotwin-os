"""
Suggestion Strategy - Adaptive confidence scoring and strategy selection.
Strategy types: nudge, warning, encouragement, optimization.
Phase 3: full adaptive confidence, persona application, pattern-type stats wired to state_store.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .state import CognitiveState, Pattern, Suggestion as SuggestionRecord, UserStats
from .logging_utils import generate_trace_id, get_trace_id

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    NUDGE = "nudge"
    WARNING = "warning"
    ENCOURAGEMENT = "encouragement"
    OPTIMIZATION = "optimization"


class SuggestionType(str, Enum):
    ROUTINE = "routine"
    EMOTIONAL_DRIFT = "emotional_drift"
    BEHAVIORAL_LOOP = "behavioral_loop"
    INTENT_PREDICTION = "intent_prediction"
    GENERAL = "general"


@dataclass
class GeneratedSuggestion:
    """Generated suggestion ready for emission."""
    suggestion_id: str
    user_id: str
    pattern_id: str
    pattern_type: str
    text: str
    strategy: str
    base_confidence: float
    adaptive_score: float
    reasoning: str
    trace_id: str
    cognitive_state: Dict[str, float]
    metadata: Dict = None


class SuggestionStrategy:
    """
    Generates suggestions with adaptive confidence and appropriate strategy.
    """

    # Strategy mappings
    STRATEGY_MAP = {
        SuggestionType.ROUTINE: {
            "high_confidence": StrategyType.NUDGE,
            "medium_confidence": StrategyType.NUDGE,
            "low_confidence": StrategyType.NUDGE,
        },
        SuggestionType.EMOTIONAL_DRIFT: {
            "high_confidence": StrategyType.ENCOURAGEMENT,
            "medium_confidence": StrategyType.ENCOURAGEMENT,
            "low_confidence": StrategyType.ENCOURAGEMENT,
        },
        SuggestionType.BEHAVIORAL_LOOP: {
            "high_confidence": StrategyType.WARNING,
            "medium_confidence": StrategyType.WARNING,
            "low_confidence": StrategyType.NUDGE,  # Softer for uncertain
        },
        SuggestionType.INTENT_PREDICTION: {
            "high_confidence": StrategyType.OPTIMIZATION,
            "medium_confidence": StrategyType.OPTIMIZATION,
            "low_confidence": StrategyType.NUDGE,
        },
    }

    # Confidence thresholds
    CONFIDENCE_HIGH = 0.8
    CONFIDENCE_MEDIUM = 0.6

    # Template texts (would be localized in production)
    TEMPLATES = {
        SuggestionType.ROUTINE: {
            StrategyType.NUDGE: [
                "Consider {action} at your usual time.",
                "It might be a good time to {action}.",
                "Your routine suggests {action} soon.",
            ]
        },
        SuggestionType.EMOTIONAL_DRIFT: {
            StrategyType.ENCOURAGEMENT: [
                "I notice you might be feeling {emotion}. Take a moment for yourself?",
                "It's okay to feel {emotion}. Would a short break help?",
                "Consider taking a calming breath - you seem {emotion}.",
            ]
        },
        SuggestionType.BEHAVIORAL_LOOP: {
            StrategyType.WARNING: [
                "You've been {behavior} for a while. Consider changing activity.",
                "This pattern may lead to {risk}. Take a break?",
                "Breaking this loop could improve your focus.",
            ],
            StrategyType.NUDGE: [
                "Maybe try something different from {behavior}?",
                "A change of pace might help - {action}?",
            ]
        },
        SuggestionType.INTENT_PREDICTION: {
            StrategyType.OPTIMIZATION: [
                "Based on your patterns, you might want to {action}.",
                "Your schedule suggests {action} would be optimal.",
                "Consider {action} - it aligns with your goals.",
            ]
        },
    }

    def __init__(self):
        self.default_templates = {
            StrategyType.NUDGE: "Consider making a change based on your current activity.",
            StrategyType.WARNING: "Your current pattern may need attention.",
            StrategyType.ENCOURAGEMENT: "You're doing well. Keep it up!",
            StrategyType.OPTIMIZATION: "An opportunity to improve your workflow.",
        }

    def select_strategy(self, pattern_type: str, confidence: float,
                       cognitive_state: Optional[Dict] = None) -> str:
        """
        Select appropriate strategy based on pattern type and confidence.
        Override based on cognitive state if needed.
        """
        cognitive_state = cognitive_state or {}

        # Get base strategy from type and confidence
        if confidence >= self.CONFIDENCE_HIGH:
            confidence_key = "high_confidence"
        elif confidence >= self.CONFIDENCE_MEDIUM:
            confidence_key = "medium_confidence"
        else:
            confidence_key = "low_confidence"

        strategy = self.STRATEGY_MAP.get(
            pattern_type, {confidence_key: StrategyType.NUDGE}
        ).get(confidence_key, StrategyType.NUDGE)

        # Override based on cognitive state
        fatigue = cognitive_state.get("fatigue", 0.5)
        if fatigue > 0.7 and strategy == StrategyType.WARNING:
            # Gentle nudge instead of warning if fatigued
            strategy = StrategyType.NUDGE

        motivation = cognitive_state.get("motivation", 0.5)
        if motivation < 0.3 and strategy == StrategyType.WARNING:
            # Switch to nudge if motivation very low
            strategy = StrategyType.NUDGE

        return strategy.value

    def calculate_adaptive_confidence(
        self,
        base_confidence: float,
        pattern_evidence: int,
        user_acceptance_rate: Optional[float] = None,
        pattern_type_acceptance_rate: Optional[float] = None,
        cognitive_state: Optional[Dict] = None,
        hours_since_last_emitted: float = 0.0
    ) -> float:
        """
        Calculate adaptive confidence with learning factors.

        Formula:
        adaptive = base * evidence_factor * user_factor * pattern_factor * state_factor * decay_factor

        Args:
            base_confidence: Base pattern confidence (0-1)
            pattern_evidence: Number of evidence points for this pattern
            user_acceptance_rate: This user's overall acceptance (0-1)
            pattern_type_acceptance_rate: Acceptance rate for this pattern type
            cognitive_state: Current cognitive state dict
            hours_since_last_emitted: Hours since last emission of this pattern

        Returns:
            Adjusted confidence (0-1)
        """
        trace_id = get_trace_id()

        # 1. Evidence factor: more evidence = more confidence (sqrt normalization)
        evidence_factor = min(1.5, (pattern_evidence ** 0.5) / (10 ** 0.5))

        # 2. User acceptance factor
        user_factor = 1.0
        if user_acceptance_rate is not None:
            if user_acceptance_rate > 0.7:
                user_factor = 1.15
            elif user_acceptance_rate < 0.3:
                user_factor = 0.7
            elif user_acceptance_rate < 0.5:
                user_factor = 0.85

        # 3. Pattern type acceptance factor
        pattern_factor = 1.0
        if pattern_type_acceptance_rate is not None:
            if pattern_type_acceptance_rate > 0.7:
                pattern_factor = 1.1
            elif pattern_type_acceptance_rate < 0.3:
                pattern_factor = 0.8

        # 4. Cognitive state factor
        state_factor = 1.0
        if cognitive_state:
            # Boost if user is motivated and focused
            motivation = cognitive_state.get("motivation", 0.5)
            focus = cognitive_state.get("focus_level", 0.5)
            state_factor = 0.8 + (motivation * 0.2) + (focus * 0.2)
            state_factor = min(1.3, state_factor)

        # 5. Time decay factor (if recently emitted, reduce confidence)
        decay_factor = 1.0
        if hours_since_last_emitted > 0:
            decay_factor = 0.95 ** hours_since_last_emitted  # 5% decay per hour

        # Combine all factors
        adaptive = base_confidence * evidence_factor * user_factor * pattern_factor * state_factor * decay_factor

        # Clamp to 0-1
        adaptive = max(0.0, min(1.0, adaptive))

        logger.debug("Adaptive confidence calculated",
                    base=base_confidence,
                    adaptive=adaptive,
                    evidence_factor=evidence_factor,
                    user_factor=user_factor,
                    pattern_factor=pattern_factor,
                    state_factor=state_factor,
                    decay_factor=decay_factor,
                    trace_id=trace_id)

        return adaptive

    def generate_text(self, pattern_type: str, strategy: str, pattern_data: Dict,
                     cognitive_state: Optional[Dict] = None) -> str:
        """
        Generate suggestion text based on template or dynamic composition.

        Args:
            pattern_type: Type of pattern
            strategy: Strategy to use
            pattern_data: Pattern metadata and details
            cognitive_state: Current cognitive state

        Returns:
            Generated suggestion text
        """
        trace_id = get_trace_id()

        # Try to get template
        templates = self.TEMPLATES.get(pattern_type, {}).get(strategy, [])

        if templates:
            # Deterministic selection by pattern_id to avoid jitter across calls
            if pattern_data.get("pattern_id"):
                idx = hash(pattern_data["pattern_id"]) % len(templates)
            else:
                idx = random.randint(0, len(templates) - 1)
            template = templates[idx]

            # Fill template placeholders
            replacements = self._extract_replacements(pattern_data, cognitive_state)
            try:
                text = template.format(**replacements)
            except KeyError as e:
                logger.warning("Template placeholder missing", missing=e, trace_id=trace_id)
                text = template
        else:
            # Fallback: compose dynamically
            text = self._compose_fallback(pattern_type, strategy, pattern_data)

        logger.debug("Suggestion text generated", pattern_type=pattern_type,
                    strategy=strategy, text=text[:100], trace_id=trace_id)
        return text

    def _extract_replacements(self, pattern_data: Dict, cognitive_state: Optional[Dict]) -> Dict:
        """Extract replacement variables from pattern data and context."""
        replacements = {}

        # From pattern data
        if "metadata" in pattern_data:
            meta = pattern_data["metadata"]
            replacements["action"] = meta.get("suggested_action", "take a break")
            replacements["behavior"] = meta.get("detected_behavior", "this activity")
            replacements["emotion"] = meta.get("detected_emotion", "stressed")
            replacements["risk"] = meta.get("potential_risk", "burnout")
            replacements["pattern"] = meta.get("pattern_description", "this pattern")

        # From cognitive state
        if cognitive_state:
            focus = cognitive_state.get("focus_level", 0.5)
            fatigue = cognitive_state.get("fatigue", 0.5)
            if focus < 0.4:
                replacements["action"] = "rest or take a break"
            elif fatigue > 0.6:
                replacements["action"] = "take a short break"

        # Defaults
        replacements.setdefault("action", "take a short break")
        replacements.setdefault("behavior", "current activity")
        replacements.setdefault("emotion", "upset")
        replacements.setdefault("risk", "reduced productivity")
        replacements.setdefault("pattern", "your behavior")

        return replacements

    def _compose_fallback(self, pattern_type: str, strategy: str, pattern_data: Dict) -> str:
        """Compose a fallback suggestion when no template exists."""
        meta = pattern_data.get("metadata", {})

        if pattern_type == "routine":
            return f"Based on your routine, consider {meta.get('suggested_action', 'taking a break')}."
        elif pattern_type == "emotional_drift":
            emotion = meta.get("detected_emotion", "stressed")
            return f"You seem {emotion}. Taking a moment to breathe might help."
        elif pattern_type == "behavioral_loop":
            behavior = meta.get("detected_behavior", "repetitive activity")
            return f"You're in a {behavior} loop. Try breaking it with a different task."
        elif pattern_type == "intent_prediction":
            return f"Ahead of your usual pattern: {meta.get('suggestion', 'Consider optimizing your workflow')}."
        else:
            return "Based on your patterns, a change might be beneficial."


class SuggestionGenerator:
    """Generates suggestions using strategy and state."""

    def __init__(self, state_store, state_model):
        self.state_store = state_store
        self.state_model = state_model
        self.strategy_engine = SuggestionStrategy()

    async def generate(
        self,
        user_id: str,
        pattern: Pattern,
        persona: Optional[Dict] = None,
        cognitive_state: Optional[Dict] = None,
        trace_id: Optional[str] = None
    ) -> GeneratedSuggestion:
        """
        Generate a suggestion for a given pattern.

        Args:
            user_id: User identifier
            pattern: Pattern that triggered suggestion
            persona: Optional user persona/character
            cognitive_state: Current cognitive state (if already fetched)
            trace_id: Trace ID for logging

        Returns:
            GeneratedSuggestion ready for emission
        """
        trace_id = trace_id or generate_trace_id()

        # Get cognitive state if not provided
        if cognitive_state is None:
            cognitive_state_obj = await self.state_model.get_state(user_id)
            cognitive_state = cognitive_state_obj.to_dict()

        # Get user stats for learning factors
        user_stats = await self.state_store.get_user_stats(user_id)

        # Get pattern acceptance history
        pattern_stats = await self._get_pattern_type_stats(user_id, pattern.pattern_type)

        # Calculate when this pattern was last emitted
        hours_since_last = 0.0
        if pattern.last_emitted:
            last_emitted = datetime.fromisoformat(
                pattern.last_emitted.rstrip("Z")
            ).replace(tzinfo=timezone.utc)
            hours_since_last = (
                datetime.now(timezone.utc) - last_emitted
            ).total_seconds() / 3600

        # Calculate adaptive confidence
        adaptive_score = self.strategy_engine.calculate_adaptive_confidence(
            base_confidence=pattern.confidence,
            pattern_evidence=pattern.evidence_count,
            user_acceptance_rate=user_stats.acceptance_rate if user_stats.total_suggestions > 0 else None,
            pattern_type_acceptance_rate=pattern_stats.get("acceptance_rate"),
            cognitive_state=cognitive_state,
            hours_since_last_emitted=hours_since_last
        )

        # Select strategy
        strategy = self.strategy_engine.select_strategy(
            pattern_type=pattern.pattern_type,
            confidence=adaptive_score,
            cognitive_state=cognitive_state
        )

        # Generate reasoning
        reasoning = self._build_reasoning(pattern, adaptive_score, user_stats, cognitive_state)

        # Generate text
        text = self.strategy_engine.generate_text(
            pattern_type=pattern.pattern_type,
            strategy=strategy,
            pattern_data=pattern.to_dict(),
            cognitive_state=cognitive_state
        )

        # Apply persona customization if available
        if persona:
            text = self._apply_persona(text, persona)

        # Build suggestion record
        suggestion_id = f"sugg:{generate_trace_id()[:12]}"

        return GeneratedSuggestion(
            suggestion_id=suggestion_id,
            user_id=user_id,
            pattern_id=pattern.pattern_id,
            pattern_type=pattern.pattern_type,
            text=text,
            strategy=strategy,
            base_confidence=pattern.confidence,
            adaptive_score=adaptive_score,
            reasoning=reasoning,
            trace_id=trace_id,
            cognitive_state=cognitive_state,
            metadata={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "persona_used": bool(persona),
            }
        )

    async def _get_pattern_type_stats(self, user_id: str, pattern_type: str) -> Dict:
        """Get acceptance stats for a specific pattern type from state_store."""
        return await self.state_store.get_pattern_type_stats(user_id, pattern_type)

    def _build_reasoning(self, pattern: Pattern, adaptive_score: float,
                        user_stats: Optional[UserStats], cognitive_state: Dict) -> str:
        """Build human-readable reasoning for the suggestion."""
        parts = []

        parts.append(f"Pattern '{pattern.pattern_type}' detected with confidence {pattern.confidence:.2f}")

        if user_stats and user_stats.total_suggestions > 0:
            parts.append(f"User acceptance rate: {user_stats.acceptance_rate:.1%}")

        if adaptive_score != pattern.confidence:
            parts.append(f"Adaptive adjustment: {adaptive_score:.2f}")

        parts.append(f"Strategy selected: {self.strategy_engine.select_strategy(pattern.pattern_type, adaptive_score, cognitive_state)}")

        if cognitive_state:
            parts.append(f"Cognitive state: focus={cognitive_state.get('focus_level', 0):.0%}, fatigue={cognitive_state.get('fatigue', 0):.0%}")

        return " | ".join(parts)

    def _apply_persona(self, text: str, persona: Dict) -> str:
        """Apply persona customization to suggestion text."""
        # Placeholder for future persona integration
        # Could adjust tone, formality, emoji usage, etc.
        persona_tone = persona.get("tone", "neutral")
        if persona_tone == "casual":
            # Add casual elements
            pass
        elif persona_tone == "formal":
            # Make more formal
            pass
        return text


logger.info("SuggestionStrategy module loaded")