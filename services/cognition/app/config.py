"""
NEUROTWIN Cognition Engine — Configuration
All settings loaded from environment with production-safe defaults.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Infrastructure
    REDIS_URL: str = "redis://neurotwin-redis:6379/0"
    COGNITION_INTERVAL: float = 2.0

    # Pattern detection
    SHORT_TERM_BUFFER_SIZE: int = 1000
    PATTERN_CONFIDENCE_THRESHOLD: float = 0.6
    ENABLED_DETECTORS: List[str] = [
        "routine", "emotional_drift", "behavioral_loop", "intent_prediction"
    ]

    # Persona service
    PERSONA_AGENT_URL: str = "http://agents:8008"
    PERSONA_CACHE_TTL: float = 300.0
    PERSONA_TIMEOUT_SECONDS: float = 0.5

    # Rate limiting and cooldowns
    MAX_SUGGESTIONS_PER_MINUTE: int = 5
    SUGGESTION_COOLDOWN_SECONDS: float = 90.0
    ACTIVE_USER_TTL_SECONDS: int = 3600

    # Cognitive state parameters
    FATIGUE_RATE_PER_INTERACTION: float = 0.01
    FATIGUE_DECAY_PER_MINUTE: float = 0.005
    FOCUS_IMPROVEMENT_RATE: float = 0.02
    MOTIVATION_BOOST_ACCEPTED: float = 0.08
    MOTIVATION_DROP_REJECTED: float = 0.05

    # Phase 3 — Learning loop
    FEEDBACK_LEARNING_FACTOR: float = 0.10
    PATTERN_FEEDBACK_BOOST: float = 0.05
    PATTERN_FEEDBACK_DROP: float = 0.03
    MIN_FEEDBACK_SAMPLES_FOR_LEARNING: int = 5

    # Phase 3 — Persona evolution
    PERSONA_EVOLUTION_ENABLED: bool = True
    PERSONA_EVOLUTION_CHANNEL: str = "neurotwin:persona_evolution"
    PERSONA_EVOLUTION_INTERVAL_HOURS: float = 1.0

    # Redis channels
    INPUT_CHANNELS: List[str] = [
        "neurotwin:behavior",
        "neurotwin:emotion",
        "neurotwin:voice",
        "neurotwin:memory",
        "neurotwin:prediction",
        "neurotwin:feedback",
    ]
    OUTPUT_CHANNEL: str = "neurotwin:suggestions"

    class Config:
        case_sensitive = False
