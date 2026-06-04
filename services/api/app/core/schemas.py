"""
NEUROTWIN OS — Pydantic Schemas
Request/Response models for all API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EmotionLabel(str, Enum):
    NEUTRAL = "neutral"
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"


class AvatarExpression(str, Enum):
    NEUTRAL = "neutral"
    SMILE = "smile"
    SURPRISED = "surprised"
    SAD = "sad"
    THINKING = "thinking"
    EXCITED = "excited"


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    locale: str = "en"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────────────

class UserPreferences(BaseModel):
    language: str = "en"
    persona_tone: str = "friendly"  # friendly | professional | playful | supportive
    memory_enabled: bool = True
    voice_enabled: bool = True
    emotion_detection: bool = True
    avatar_style: str = "live2d"
    flirt_level: int = Field(0, ge=0, le=3)  # 0=off, 1=light, 2=moderate, 3=playful


class UserProfile(BaseModel):
    id: UUID
    email: str
    name: str
    locale: str
    preferences: UserPreferences
    created_at: datetime
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UpdatePreferencesRequest(BaseModel):
    preferences: UserPreferences


# ── Conversation ──────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    session_id: Optional[str] = None  # comes from URL path — not required in body
    content: str = Field(..., min_length=1, max_length=4096)
    emotion_hint: Optional[EmotionLabel] = None
    emotion_source: Optional[str] = Field(None, max_length=20)
    emotion_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    arousal: Optional[float] = Field(None, ge=0.0, le=1.0)
    valence: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        return v.strip()

    @field_validator("emotion_source")
    @classmethod
    def normalize_emotion_source(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().lower()
        return normalized or None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: Role
    content: str
    emotion: Optional[EmotionLabel] = None
    avatar_command: Optional[Dict[str, Any]] = None
    tts_url: Optional[str] = None
    created_at: datetime
    latency_ms: Optional[float] = None


class ConversationHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]
    total: int


class StreamChunk(BaseModel):
    """Server-sent event chunk for streaming responses."""
    type: str  # "token" | "done" | "error" | "avatar"
    data: str = ""
    metadata: Optional[Dict[str, Any]] = None


class SessionCreateRequest(BaseModel):
    persona_override: Optional[str] = None
    context: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    persona: str


# ── Avatar ────────────────────────────────────────────────────────────────────

class AvatarSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    voice_id: Optional[str] = None
    emotion: EmotionLabel = EmotionLabel.NEUTRAL
    speed: float = Field(1.0, ge=0.5, le=2.0)


class AvatarExpressionRequest(BaseModel):
    expression: AvatarExpression
    intensity: float = Field(0.8, ge=0.0, le=1.0)
    duration_ms: int = Field(2000, ge=100, le=10000)
    blend: bool = True  # blend with previous expression


class AvatarStateResponse(BaseModel):
    avatar_id: str
    current_expression: AvatarExpression
    is_speaking: bool
    position: Dict[str, float]
    animation_queue_length: int


class VisemeFrame(BaseModel):
    viseme_id: int  # 0–21 (standard viseme set)
    start_ms: int
    end_ms: int
    weight: float = 1.0


class LipSyncResponse(BaseModel):
    audio_url: str
    duration_ms: int
    viseme_frames: List[VisemeFrame]
    expression_hints: List[Dict[str, Any]]


# ── Memory ────────────────────────────────────────────────────────────────────

class MemoryEntry(BaseModel):
    id: str
    type: str
    summary: str
    timestamp: datetime
    importance: float
    emotion: Optional[str] = None


class MemoryListResponse(BaseModel):
    memories: List[MemoryEntry]
    total: int
    has_more: bool


class MemoryDeleteRequest(BaseModel):
    memory_ids: List[str]


# ── Analytics ─────────────────────────────────────────────────────────────────

class MoodDataPoint(BaseModel):
    timestamp: datetime
    emotion: EmotionLabel
    intensity: float
    session_id: Optional[str] = None


class MoodTimelineResponse(BaseModel):
    user_id: str
    period_days: int
    data_points: List[MoodDataPoint]
    dominant_emotion: EmotionLabel
    average_intensity: float


class TopicFrequency(BaseModel):
    topic: str
    count: int
    last_mentioned: datetime


class AnalyticsSummaryResponse(BaseModel):
    user_id: str
    period_days: int
    total_sessions: int
    total_messages: int
    avg_session_length_minutes: float
    top_topics: List[TopicFrequency]
    mood_timeline: List[MoodDataPoint]
    engagement_score: float


# ── Perception / STT ──────────────────────────────────────────────────────────

class TranscriptionResult(BaseModel):
    text: str
    confidence: float
    language: str = "en"
    duration_seconds: float
    words: Optional[List[Dict[str, Any]]] = None  # word-level timestamps


class EmotionDetectionResult(BaseModel):
    dominant: EmotionLabel
    scores: Dict[str, float]  # emotion → probability
    arousal: float = 0.5  # 0=calm, 1=excited
    valence: float = 0.5  # 0=negative, 1=positive
    confidence: float


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    db_connected: bool = True
    redis_connected: bool = True
    llm_available: bool = True
