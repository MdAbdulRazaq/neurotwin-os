"""
NEUROTWIN OS — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class _FixedEnvSource(EnvSettingsSource):
    """Override decode_complex_value so comma-separated ALLOWED_ORIGINS
    is passed raw to the field_validator instead of crashing on json.loads."""
    def decode_complex_value(self, field_name, field, value):
        if field_name.upper() == "ALLOWED_ORIGINS" and isinstance(value, str) and not value.strip().startswith("["):
            return value  # hand raw string to field_validator, skip json.loads
        return super().decode_complex_value(field_name, field, value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, **kwargs):
        return (init_settings, _FixedEnvSource(settings_cls), dotenv_settings)

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "NEUROTWIN OS"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: SecretStr = SecretStr("change-me-in-production-use-256bit-random-key")
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://app.neurotwin.ai"]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://neurotwin:password@localhost:5432/neurotwin_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 3600

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_BASE_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[SecretStr] = None
    LLM_MODEL: str = "gpt-4o"
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.7
    LLM_STREAM: bool = True

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # ── Vector DB (Pinecone) ──────────────────────────────────────────────────
    PINECONE_API_KEY: Optional[SecretStr] = None
    PINECONE_ENVIRONMENT: str = "us-east1-gcp"
    PINECONE_INDEX_NAME: str = "neurotwin-memory"
    VECTOR_TOP_K: int = 8

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("neo4j")

    # ── Speech ────────────────────────────────────────────────────────────────
    STT_PROVIDER: str = "deepgram"  # "deepgram" | "whisper" | "vosk"
    DEEPGRAM_API_KEY: Optional[SecretStr] = None
    TTS_PROVIDER: str = "elevenlabs"  # "elevenlabs" | "coqui"
    ELEVENLABS_API_KEY: Optional[SecretStr] = None
    ELEVENLABS_VOICE_ID: str = "EXAVITQu4vr4xnSDxMaL"

    # ── Avatar ────────────────────────────────────────────────────────────────
    AVATAR_PROVIDER: str = "live2d"  # "live2d" | "metahuman" | "heygen"
    HEYGEN_API_KEY: Optional[SecretStr] = None

    # ── Storage (S3-compatible) ───────────────────────────────────────────────
    S3_ENDPOINT: Optional[str] = None
    S3_BUCKET: str = "neurotwin-media"
    S3_ACCESS_KEY: Optional[SecretStr] = None
    S3_SECRET_KEY: Optional[SecretStr] = None

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # ── Monitoring ────────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
