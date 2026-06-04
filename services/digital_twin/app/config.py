"""
NEUROTWIN Digital Twin — Configuration (Phase 4)
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Infrastructure
    REDIS_URL:   str = "redis://neurotwin-redis:6379/0"
    NEO4J_URI:   str = "bolt://neurotwin-neo4j:7687"
    NEO4J_USER:  str = "neo4j"
    NEO4J_PASSWORD: str = "neurotwin_password"

    # Service URLs
    COGNITION_URL:  str = "http://cognition:8013"
    AGENTS_URL:     str = "http://agents:8008"

    # Twin behaviour
    TWIN_SYNC_INTERVAL:          float = 30.0   # seconds between full sync cycles
    PATTERN_TO_TRAIT_THRESHOLD:  int   = 3       # min pattern occurrences → trait
    TRAIT_CONFIDENCE_FLOOR:      float = 0.3
    PREDICTION_HORIZON_HOURS:    int   = 24
    TIMELINE_RETENTION_DAYS:     int   = 90
    PROFILE_CACHE_TTL:           int   = 300     # 5-minute Redis cache for profiles

    # Redis channels
    INPUT_CHANNELS: List[str] = [
        "neurotwin:behavior",
        "neurotwin:emotion",
        "neurotwin:feedback",
        "neurotwin:suggestions",
        "neurotwin:twin_update",
    ]

    class Config:
        case_sensitive = False
