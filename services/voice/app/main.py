"""
NEUROTWIN OS — Voice Agent
TTS + STT with event publishing for lip-sync coordination.
Emits speech_start/speech_end events for BehaviorAgent.
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from .lip_sync import text_to_viseme_cues

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware
from services.common.http_client import get_traced_client
from services.common.redis_events import publish_event

setup_logging(service_name="neurotwin.voice")
logger = logging.getLogger("neurotwin.voice")

app = FastAPI(title="voice-agent", version="1.0.0")
app.add_middleware(TraceMiddleware)

# ── Configuration ─────────────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

_redis: Optional[aioredis.Redis] = None

# ── Schemas ────────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    voice_id: Optional[str] = Field(None, description="ElevenLabs voice ID")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier")

class STTResponse(BaseModel):
    text: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    emotion: Optional[str] = None
    duration_seconds: Optional[float] = None

class VoiceEvent(BaseModel):
    event: str = Field(..., description="Event type: speech_start, speech_end, listening, transcript")
    session_id: Optional[str] = None
    user_id: str = Field(..., description="User identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)

# ── Redis Helper ───────────────────────────────────────────────────────────────

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis

async def publish_voice_event(event: str, user_id: str, session_id: Optional[str] = None, data: Optional[Dict] = None):
    """Publish voice event to Redis for BehaviorAgent consumption."""
    redis_client = await get_redis()
    payload = VoiceEvent(
        event=event,
        session_id=session_id,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        data=data or {}
    ).dict()
    try:
        await publish_event(channel="neurotwin:voice", data=payload, redis_client=redis_client)
        logger.debug(f"Voice event: {event} for user {user_id}")
    except Exception as e:
        logger.error(f"Voice publish failed: {e}")

# ── TTS Implementation ─────────────────────────────────────────────────────────

async def generate_tts_elevenlabs(text: str, voice_id: str, speed: float = 1.0) -> bytes:
    """Generate TTS using ElevenLabs API."""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    async with get_traced_client(timeout=30.0) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": "eleven_flash_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "speed": speed
                }
            },
            headers={"xi-api-key": ELEVENLABS_API_KEY}
        )
        response.raise_for_status()
        return response.content

async def generate_tts_mock(text: str) -> bytes:
    """Mock TTS for development - returns silent audio."""
    # Return minimal valid MP3 (1 second of silence)
    # In production, implement proper TTS or use browser SpeechSynthesis
    await asyncio.sleep(0.1)  # Simulate processing
    return b''  # Empty for dev

# ── STT Implementation (Placeholder) ───────────────────────────────────────────

async def transcribe_audio(audio_bytes: bytes, provider: str = "deepgram") -> STTResponse:
    """Transcribe audio using configured STT provider."""
    if provider == "deepgram" and DEEPGRAM_API_KEY:
        # Implement Deepgram streaming/batch
        # For now, return mock
        await asyncio.sleep(0.2)
        return STTResponse(
            text="[transcribed text]",
            confidence=0.95,
            duration_seconds=1.0
        )
    else:
        # Whisper fallback
        await asyncio.sleep(0.3)
        return STTResponse(
            text="[whisper transcription]",
            confidence=0.90,
            duration_seconds=1.0
        )

# ── API Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "voice",
        "tts_configured": bool(ELEVENLABS_API_KEY),
        "stt_configured": bool(DEEPGRAM_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/v1/voice/speak")
async def speak(request: TTSRequest):
    """
    Convert text to speech and publish speech_start/speech_end events.
    This is the critical endpoint that drives lip-sync state.
    """
    logger.info(f"TTS request for user {request.user_id}: {request.text[:50]}...")

    # 1. Publish speech_start event (BehaviorAgent will set SPEAKING)
    await publish_voice_event(
        "speech_start",
        user_id=request.user_id,
        session_id=request.session_id,
        data={"text_length": len(request.text), "voice_id": request.voice_id or ELEVENLABS_VOICE_ID}
    )

    try:
        # 2. Generate TTS audio
        if ELEVENLABS_API_KEY:
            audio_data = await generate_tts_elevenlabs(
                request.text,
                request.voice_id or ELEVENLABS_VOICE_ID,
                request.speed
            )
            # Estimate duration: ~150 words per minute
            word_count = len(request.text.split())
            duration = max(0.5, word_count / 150 * 60)
        else:
            # Mock mode - simulate delay
            word_count = len(request.text.split())
            duration = max(0.5, word_count / 150 * 60)
            await asyncio.sleep(duration * 0.5)  # Simulate speaking time
            audio_data = b''

        # 3.5 Generate and publish lip-sync cues
        try:
            cues = text_to_viseme_cues(request.text, duration)
            redis_client = await get_redis()
            await publish_event(
                channel="neurotwin:avatar_lipsync",
                data={
                    "user_id": request.user_id,
                    "session_id": request.session_id,
                    "cues": cues,
                    "duration": duration,
                    "timestamp": datetime.utcnow().isoformat()
                },
                redis_client=redis_client
            )
        except Exception as e:
            logger.error(f"Lip-sync generation failed: {e}")

        # 3. Publish speech_end event (BehaviorAgent will return to IDLE)
        await publish_voice_event(
            "speech_end",
            user_id=request.user_id,
            session_id=request.session_id,
            data={"duration": duration}
        )

        # 4. Return audio (in production, would return URL to stored file)
        # For now, return base64 encoded audio
        audio_b64 = base64.b64encode(audio_data).decode('utf-8') if audio_data else ""

        logger.info(f"TTS complete: {duration:.2f}s for user {request.user_id}")

        return {
            "audio_data": audio_b64,
            "content_type": "audio/mpeg",
            "duration": duration,
            "voice_id": request.voice_id or ELEVENLABS_VOICE_ID,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        # Still send speech_end to avoid stuck SPEAKING state
        await publish_voice_event("speech_end", user_id=request.user_id, session_id=request.session_id)
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@app.websocket("/ws/voice/stream")
async def ws_voice_stream(websocket: WebSocket):
    """
    Real-time streaming STT WebSocket.
    Client sends audio chunks, server returns transcript + emotion.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    user_id = "unknown"  # Would be extracted from auth token

    try:
        # Publish listening start
        await publish_voice_event("listening", user_id=user_id, session_id=session_id)

        buffer = bytearray()
        while True:
            data = await websocket.receive_bytes()
            buffer.extend(data)

            # Process in 1-second chunks (16000 samples for 16kHz)
            if len(buffer) >= 32000:
                audio_segment = bytes(buffer[:32000])
                buffer.clear()

                # Transcribe (mock for now)
                result = await transcribe_audio(audio_segment)

                # Send transcript
                await websocket.send_json({
                    "type": "transcript",
                    "text": result.text,
                    "confidence": result.confidence,
                    "emotion": result.emotion,
                    "is_final": False
                })

                # Publish transcript event for orchestrator memory
                # (Would send to neurotwin:conversations)
                # For now, just log

    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        await websocket.close(code=1011)

@app.post("/v1/voice/transcribe")
async def transcribe(
    audio: bytes = None,
    file: Optional[Any] = None
):
    """
    One-off transcription endpoint.
    Accepts audio file upload, returns text + optional emotion.
    """
    audio_bytes = audio or (await file.read() if file else b'')
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio provided")

    result = await transcribe_audio(audio_bytes)
    return result.dict()

# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _redis
    try:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        logger.info("VoiceAgent started - Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    global _redis
    if _redis:
        await _redis.close()
        logger.info("VoiceAgent Redis closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8006, reload=True)
