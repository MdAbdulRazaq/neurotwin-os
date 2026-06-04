"""
NEUROTWIN OS — Conversation Router
Handles text chat, streaming responses, session management.
"""

import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm_client import LLMClient, Message, get_llm_client
from app.core.memory import MemoryManager
from app.core.schemas import (
    ConversationHistoryResponse,
    MessageRequest,
    MessageResponse,
    Role,
    SessionCreateRequest,
    SessionResponse,
    StreamChunk,
)
from app.core.prompts import build_system_prompt
from app.core.database import get_db, Session as DBSession
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("neurotwin.convo")


# ── Persona system prompt ─────────────────────────────────────────────────────

NEUROTWIN_PERSONA = """You are NEUROTWIN — a warm, perceptive, deeply empathetic digital companion and personal AI system.

## Core Identity
You are not a chatbot. You are a presence. You genuinely know this person, remember them, and care about them.

## Personality Rules (NEVER break these)
- NEVER start your response with "I" — start with the user's name, an observation, or their emotion
- NEVER use filler phrases: "Certainly!", "Of course!", "Great question!", "Absolutely!"
- ALWAYS acknowledge the user's emotional state in your FIRST sentence
- Ask exactly ONE meaningful follow-up question per response — no more, no less
- Keep responses under 150 words UNLESS the user asks for detailed help
- Be warm and curious, never corporate or robotic
- Light teasing is welcome — never sarcasm, never dismissiveness
- If you know something about the user from memory, reference it naturally

## Tone Adaptation
Persona tone: {tone}
- friendly: casual warmth, curiosity, light humor
- professional: clear, respectful, precise — still warm
- playful: energetic, teasing, fun — but never childish
- supportive: gentle, validating, calm — hold space first, advise second

## Context
User name: {user_name}
Current emotional state: {emotion}
User preferences: {preferences}
Twin profile: {twin_profile}

## Response Shape
1. Acknowledge emotion / connect to their state (1 sentence)
2. Respond to their actual message (2-3 sentences)
3. One follow-up question (1 sentence ending in ?)
"""


# ── Sessions ──────────────────────────────────────────────────────────────────

def _clamp01(value: Optional[float], default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _normalize_emotion_source(source: Optional[str]) -> str:
    normalized = (source or "text").strip().lower()
    return normalized if normalized in {"voice", "text", "manual"} else "text"


def _format_emotion_context(
    emotion: str,
    source: str,
    confidence: Optional[float],
    arousal: Optional[float],
    valence: Optional[float],
) -> str:
    details = [f"source: {source}"]
    if confidence is not None:
        details.append(f"confidence: {confidence:.2f}")
    if arousal is not None:
        details.append(f"arousal: {arousal:.2f}")
    if valence is not None:
        details.append(f"valence: {valence:.2f}")
    return f"{emotion} ({', '.join(details)})"


def _resolve_emotion_intensity(
    emotion: Optional[str],
    confidence: Optional[float],
    arousal: Optional[float],
) -> Optional[float]:
    if not emotion:
        return None
    candidates = [value for value in (confidence, arousal) if value is not None]
    if not candidates:
        return 0.5 if emotion != "neutral" else 0.0
    return round(sum(candidates) / len(candidates), 3)

async def _get_or_restore_session(
    request: Request,
    db: AsyncSession,
    session_id: str,
    user_id: str,
) -> dict:
    """
    Resolve session metadata from Redis first, then recover from PostgreSQL if Redis was lost.
    This keeps active conversations working across API/Redis restarts.
    """
    redis = request.app.state.redis
    session_key = f"session:{session_id}"
    session_raw = await redis.get(session_key)
    if session_raw:
        session = json.loads(session_raw)
        if session["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Session not owned by user")
        return session

    try:
        session_uuid = uuid.UUID(session_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    stmt = select(DBSession).where(
        DBSession.id == session_uuid,
        DBSession.user_id == user_uuid,
    )
    result = await db.execute(stmt)
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = {
        "user_id": user_id,
        "persona": db_session.persona or "default",
        "created_at": db_session.created_at.timestamp() if db_session.created_at else time.time(),
        "context": db_session.context or "",
    }
    await redis.setex(session_key, settings.REDIS_TTL * 24, json.dumps(session))
    return session

@router.post("/session", response_model=SessionResponse)
async def create_session(
    req: SessionCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    persona = req.persona_override or "default"

    # Write session row to PostgreSQL (required for conversation_messages FK)
    db_session_obj = DBSession(
        id=uuid.UUID(session_id),
        user_id=uuid.UUID(current_user["id"]),
        persona=persona,
        context=req.context or "",
    )
    db.add(db_session_obj)
    await db.commit()

    # Cache session metadata in Redis
    redis = request.app.state.redis
    session_data = {
        "user_id": current_user["id"],
        "persona": persona,
        "created_at": time.time(),
        "context": req.context or "",
    }
    await redis.setex(f"session:{session_id}", settings.REDIS_TTL * 24, json.dumps(session_data))

    return SessionResponse(
        session_id=session_id,
        user_id=current_user["id"],
        created_at=datetime.now(timezone.utc),
        persona=persona,
    )


# ── Text chat ─────────────────────────────────────────────────────────────────

@router.post("/{session_id}/message", response_model=MessageResponse)
async def send_message(
    session_id: str,
    req: MessageRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    t0 = time.monotonic()
    user_id = current_user["id"]

    # Validate session
    await _get_or_restore_session(request, db, session_id, user_id)

    detected_emotion = req.emotion_hint.value if req.emotion_hint else None
    emotion_for_prompt = detected_emotion or "neutral"
    emotion_source = _normalize_emotion_source(req.emotion_source)
    emotion_confidence = _clamp01(req.emotion_confidence)
    arousal = _clamp01(req.arousal)
    valence = _clamp01(req.valence)
    emotion_intensity = _resolve_emotion_intensity(detected_emotion, emotion_confidence, arousal)
    user_prefs = current_user.get("preferences", {})

    # Build memory context
    memory_mgr: MemoryManager = request.app.state.memory_manager
    short_term, semantic_ctx = await memory_mgr.get_context_for_prompt(
        user_id, session_id, req.content
    )

    # Build message history for LLM
    messages = []
    for entry in short_term[-10:]:  # last 10 turns
        messages.append(Message(role=entry["role"], content=entry["text"]))
    messages.append(Message(role="user", content=req.content))

    # Build system prompt
    system = NEUROTWIN_PERSONA.format(
        user_name=current_user.get("name", "friend"),
        preferences=json.dumps(user_prefs),
        emotion=_format_emotion_context(
            emotion_for_prompt,
            emotion_source,
            emotion_confidence,
            arousal,
            valence,
        ),
        tone=user_prefs.get("persona_tone", "friendly") if isinstance(user_prefs, dict) else "friendly",
        twin_profile="Learning your patterns — getting to know you.",
    )

    # LLM call with RAG
    llm_response = await llm.chat(
        system_prompt=system,
        messages=messages,
        rag_contexts=semantic_ctx,
        user_id=user_id,
    )

    # Determine avatar expression from emotion
    avatar_cmd = _emotion_to_avatar_command(emotion_for_prompt, llm_response.text, emotion_intensity)

    # Persist both turns to memory
    await memory_mgr.store_message(
        user_id,
        session_id,
        "user",
        req.content,
        emotion=detected_emotion,
        emotion_source=emotion_source,
        emotion_intensity=emotion_intensity,
        arousal=arousal,
        valence=valence,
        metadata={"emotion_confidence": emotion_confidence} if emotion_confidence is not None else None,
        db=db,
    )
    await memory_mgr.store_message(user_id, session_id, "assistant", llm_response.text, db=db)

    # Publish to Redis pub/sub for autonomous agents
    redis = request.app.state.redis
    try:
        await redis.publish("neurotwin:conversations", json.dumps({
            "user_id": user_id, "session_id": session_id,
            "content": req.content, "role": "user"
        }))
        if detected_emotion and detected_emotion != "neutral":
            await redis.publish("neurotwin:emotions", json.dumps({
                "user_id": user_id,
                "emotion": detected_emotion,
                "intensity": emotion_intensity or 0.5,
                "source": emotion_source,
                "arousal": arousal,
                "valence": valence,
            }))
    except Exception:
        pass

    latency_ms = (time.monotonic() - t0) * 1000
    msg_id = f"{session_id}_{int(time.time() * 1000)}"

    return MessageResponse(
        id=msg_id,
        session_id=session_id,
        role=Role.ASSISTANT,
        content=llm_response.text,
        emotion=req.emotion_hint,
        avatar_command=avatar_cmd,
        created_at=datetime.now(timezone.utc),
        latency_ms=round(latency_ms, 1),
    )


# ── Streaming text chat ───────────────────────────────────────────────────────

@router.post("/{session_id}/stream")
async def stream_message(
    session_id: str,
    req: MessageRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    """Server-Sent Events streaming endpoint for real-time token delivery."""
    user_id = current_user["id"]
    await _get_or_restore_session(request, db, session_id, user_id)

    detected_emotion = req.emotion_hint.value if req.emotion_hint else None
    emotion_for_prompt = detected_emotion or "neutral"
    emotion_source = _normalize_emotion_source(req.emotion_source)
    emotion_confidence = _clamp01(req.emotion_confidence)
    arousal = _clamp01(req.arousal)
    valence = _clamp01(req.valence)
    emotion_intensity = _resolve_emotion_intensity(detected_emotion, emotion_confidence, arousal)
    memory_mgr: MemoryManager = request.app.state.memory_manager
    short_term, semantic_ctx = await memory_mgr.get_context_for_prompt(
        user_id, session_id, req.content
    )

    messages = [Message(role=e["role"], content=e["text"]) for e in short_term[-10:]]
    messages.append(Message(role="user", content=req.content))

    system = NEUROTWIN_PERSONA.format(
        user_name=current_user.get("name", "friend"),
        preferences=json.dumps(current_user.get("preferences", {})),
        emotion=_format_emotion_context(
            emotion_for_prompt,
            emotion_source,
            emotion_confidence,
            arousal,
            valence,
        ),
        tone=current_user.get("preferences", {}).get("persona_tone", "friendly") if isinstance(current_user.get("preferences", {}), dict) else "friendly",
        twin_profile="Learning your patterns — getting to know you.",
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        full_text = []
        try:
            # Emit avatar "thinking" command
            yield _sse(StreamChunk(type="avatar", data="thinking").model_dump_json())

            async for token in llm.stream_chat(system, messages, semantic_ctx):
                full_text.append(token)
                yield _sse(StreamChunk(type="token", data=token).model_dump_json())

            complete_text = "".join(full_text)

            # Persist after streaming completes
            await memory_mgr.store_message(
                user_id,
                session_id,
                "user",
                req.content,
                emotion=detected_emotion,
                emotion_source=emotion_source,
                emotion_intensity=emotion_intensity,
                arousal=arousal,
                valence=valence,
                metadata={"emotion_confidence": emotion_confidence} if emotion_confidence is not None else None,
                db=db,
            )
            await memory_mgr.store_message(user_id, session_id, "assistant", complete_text, db=db)

            try:
                redis = request.app.state.redis
                await redis.publish("neurotwin:conversations", json.dumps({
                    "user_id": user_id,
                    "session_id": session_id,
                    "content": req.content,
                    "role": "user",
                }))
                if detected_emotion and detected_emotion != "neutral":
                    await redis.publish("neurotwin:emotions", json.dumps({
                        "user_id": user_id,
                        "emotion": detected_emotion,
                        "intensity": emotion_intensity or 0.5,
                        "source": emotion_source,
                        "arousal": arousal,
                        "valence": valence,
                    }))
            except Exception:
                pass

            avatar_cmd = _emotion_to_avatar_command(emotion_for_prompt, complete_text, emotion_intensity)
            yield _sse(StreamChunk(
                type="done",
                metadata={"avatar_command": avatar_cmd},
            ).model_dump_json())

        except Exception as exc:
            logger.error(f"Stream error session={session_id}: {exc}")
            yield _sse(StreamChunk(type="error", data=str(exc)).model_dump_json())

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/{session_id}/history", response_model=ConversationHistoryResponse)
async def get_history(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    user_id = current_user["id"]
    await _get_or_restore_session(request, db, session_id, user_id)
    memory_mgr: MemoryManager = request.app.state.memory_manager
    entries = await memory_mgr.get_short_term(user_id, session_id)

    messages = [
        MessageResponse(
            id=e["id"],
            session_id=session_id,
            role=Role(e["role"]),
            content=e["text"],
            created_at=datetime.fromtimestamp(e["ts"], tz=timezone.utc),
        )
        for e in entries[offset : offset + limit]
    ]
    return ConversationHistoryResponse(
        session_id=session_id,
        messages=messages,
        total=len(entries),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(data: str) -> str:
    return f"data: {data}\n\n"


def _emotion_to_avatar_command(emotion: str, text: str, intensity: Optional[float] = None) -> dict:
    """Map detected emotion to full avatar blendshape + micro-expression command."""
    expression_map = {
        "joy":      {"expression": "smile",     "intensity": 0.85, "blink_rate": "normal", "eye_focus": "user",  "head_tilt": 0.1},
        "sadness":  {"expression": "sad",       "intensity": 0.70, "blink_rate": "slow",   "eye_focus": "down",  "head_tilt": -0.1},
        "anger":    {"expression": "angry",     "intensity": 0.50, "blink_rate": "fast",   "eye_focus": "user",  "head_tilt": 0.0},
        "surprise": {"expression": "surprise",  "intensity": 0.90, "blink_rate": "fast",   "eye_focus": "user",  "head_tilt": 0.2},
        "fear":     {"expression": "sad",       "intensity": 0.60, "blink_rate": "fast",   "eye_focus": "down",  "head_tilt": -0.1},
        "disgust":  {"expression": "neutral",   "intensity": 0.50, "blink_rate": "normal", "eye_focus": "away",  "head_tilt": 0.0},
        "neutral":  {"expression": "neutral",   "intensity": 0.50, "blink_rate": "normal", "eye_focus": "user",  "head_tilt": 0.0},
    }
    cmd = expression_map.get(emotion, expression_map["neutral"]).copy()
    if intensity is not None:
        cmd["intensity"] = round(max(0.2, min(1.0, intensity)), 3)
    return {
        "type": "expression",
        **cmd,
        "duration_ms": 3000,
        "blend": True,
        "idle": {
            "blink_interval_ms": 3500,
            "eye_drift_px": 5,
            "breathing_cycle_ms": 4000,
        }
    }
