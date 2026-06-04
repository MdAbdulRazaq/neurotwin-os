"""
NEUROTWIN OS — Avatar Router
Controls avatar expressions, lip-sync, TTS synthesis, and animation state.
"""

import asyncio
import base64
import hashlib
import logging
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.schemas import (
    AvatarExpressionRequest,
    AvatarSpeakRequest,
    AvatarStateResponse,
    AvatarExpression,
    LipSyncResponse,
    VisemeFrame,
)
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("neurotwin.avatar")


# ── Phoneme → Viseme mapping ──────────────────────────────────────────────────
# Standard 22-viseme set (Microsoft Speech SDK compatible)
PHONEME_TO_VISEME = {
    "AA": 2, "AE": 2, "AH": 2, "AO": 3, "AW": 3,
    "AY": 2, "B": 21, "CH": 16, "D": 19, "DH": 17,
    "EH": 4, "ER": 5, "EY": 4, "F": 18, "G": 20,
    "HH": 12, "IH": 6, "IY": 6, "JH": 16, "K": 20,
    "L": 14, "M": 21, "N": 19, "NG": 20, "OW": 8,
    "OY": 8, "P": 21, "R": 13, "S": 15, "SH": 16,
    "T": 19, "TH": 17, "UH": 7, "UW": 9, "V": 18,
    "W": 11, "Y": 10, "Z": 15, "ZH": 16, "SIL": 0,
}


# ── TTS Clients ───────────────────────────────────────────────────────────────

class ElevenLabsClient:
    """ElevenLabs TTS streaming client."""

    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0)
        self.api_key = settings.ELEVENLABS_API_KEY.get_secret_value() if settings.ELEVENLABS_API_KEY else ""
        self.default_voice = settings.ELEVENLABS_VOICE_ID

    async def synthesize(self, text: str, voice_id: Optional[str] = None, speed: float = 1.0) -> bytes:
        """Synthesize text to speech, return raw audio bytes (mp3)."""
        voice = voice_id or self.default_voice
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "speed": speed},
        }
        resp = await self._http.post(
            f"{self.BASE}/text-to-speech/{voice}/stream",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.content

    async def stream_synthesize(self, text: str, voice_id: Optional[str] = None):
        """Streaming TTS — yields audio chunks as they arrive."""
        voice = voice_id or self.default_voice
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
        }
        async with self._http.stream(
            "POST",
            f"{self.BASE}/text-to-speech/{voice}/stream",
            headers=headers,
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=4096):
                yield chunk

    async def close(self):
        await self._http.aclose()


class LipSyncEngine:
    """
    Phoneme-based lip-sync engine.
    Converts TTS output + phoneme alignment into viseme frames.
    In production, replace _forced_align with Gentle or Montreal Forced Aligner.
    """

    FRAME_DURATION_MS = 40  # 25fps

    def generate_visemes(self, text: str, duration_ms: int) -> List[VisemeFrame]:
        """Generate viseme frames for given text and audio duration."""
        words = text.split()
        if not words:
            return [VisemeFrame(viseme_id=0, start_ms=0, end_ms=duration_ms, weight=1.0)]

        ms_per_word = duration_ms / len(words)
        frames = []

        for i, word in enumerate(words):
            start = int(i * ms_per_word)
            end = int((i + 1) * ms_per_word)
            # Simple: map first two letters to approximate phoneme
            phoneme = self._word_to_phoneme(word)
            viseme_id = PHONEME_TO_VISEME.get(phoneme, 0)
            frames.append(VisemeFrame(
                viseme_id=viseme_id,
                start_ms=start,
                end_ms=end,
                weight=0.9,
            ))

        return frames

    def _word_to_phoneme(self, word: str) -> str:
        """Heuristic phoneme from first syllable (production: use G2P model)."""
        w = word.upper().strip(".,!?;:")
        if not w:
            return "SIL"
        vowel_map = {"A": "AH", "E": "EH", "I": "IH", "O": "OW", "U": "UH"}
        for i, ch in enumerate(w):
            if ch in vowel_map:
                return vowel_map[ch]
        return "SIL"


# ── Singletons ────────────────────────────────────────────────────────────────
_tts_client = ElevenLabsClient()
_lipsync = LipSyncEngine()


# ── State store (in-memory for MVP; use Redis in production) ──────────────────
_avatar_states: dict = {}  # avatar_id → state dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{avatar_id}/speak", response_model=LipSyncResponse)
async def avatar_speak(
    avatar_id: str,
    req: AvatarSpeakRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Synthesize speech for avatar + generate lip-sync data."""
    try:
        audio_bytes = await _tts_client.synthesize(req.text, req.voice_id, req.speed)
    except httpx.HTTPError as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(status_code=502, detail=f"TTS service error: {e}")

    # Store audio in Redis temporarily
    redis = request.app.state.redis
    audio_key = f"audio:{avatar_id}:{hashlib.md5(req.text.encode()).hexdigest()}"
    await redis.setex(audio_key, 300, base64.b64encode(audio_bytes).decode())

    duration_ms = len(audio_bytes) // 32  # rough estimate: 32 bytes/ms at 256kbps
    viseme_frames = _lipsync.generate_visemes(req.text, duration_ms)

    # Expression hints based on emotion
    expression_hints = _text_to_expression_hints(req.text, req.emotion)

    # Update avatar state
    _avatar_states[avatar_id] = {
        "is_speaking": True,
        "current_expression": req.emotion.value,
        "queue_length": 1,
    }

    # Clear speaking state after audio completes
    background_tasks.add_task(_clear_speaking_state, avatar_id, duration_ms / 1000)

    return LipSyncResponse(
        audio_url=f"/v1/avatar/{avatar_id}/audio/{audio_key.split(':')[-1]}",
        duration_ms=duration_ms,
        viseme_frames=viseme_frames,
        expression_hints=expression_hints,
    )


@router.post("/{avatar_id}/expression")
async def set_expression(
    avatar_id: str,
    req: AvatarExpressionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Directly set avatar expression blendshape."""
    _avatar_states[avatar_id] = {
        "current_expression": req.expression.value,
        "is_speaking": _avatar_states.get(avatar_id, {}).get("is_speaking", False),
        "queue_length": 0,
    }

    # Broadcast to WebSocket if available
    return {
        "avatar_id": avatar_id,
        "expression": req.expression,
        "intensity": req.intensity,
        "duration_ms": req.duration_ms,
        "blend": req.blend,
        "applied_at": time.time(),
    }


@router.get("/{avatar_id}/state", response_model=AvatarStateResponse)
async def get_avatar_state(
    avatar_id: str,
    current_user: dict = Depends(get_current_user),
):
    state = _avatar_states.get(avatar_id, {})
    return AvatarStateResponse(
        avatar_id=avatar_id,
        current_expression=AvatarExpression(state.get("current_expression", "neutral")),
        is_speaking=state.get("is_speaking", False),
        position={"x": 0.0, "y": 0.0, "z": 0.0},
        animation_queue_length=state.get("queue_length", 0),
    )


@router.get("/{avatar_id}/audio/{audio_id}")
async def get_audio(
    avatar_id: str,
    audio_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Serve cached TTS audio."""
    redis = request.app.state.redis
    audio_key = f"audio:{avatar_id}:{audio_id}"
    b64 = await redis.get(audio_key)
    if not b64:
        raise HTTPException(status_code=404, detail="Audio not found or expired")
    audio_bytes = base64.b64decode(b64)
    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline"},
    )


@router.post("/{avatar_id}/stream-speak")
async def stream_avatar_speak(
    avatar_id: str,
    req: AvatarSpeakRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream TTS audio directly to client."""
    async def audio_generator():
        async for chunk in _tts_client.stream_synthesize(req.text, req.voice_id):
            yield chunk

    return StreamingResponse(
        audio_generator(),
        media_type="audio/mpeg",
        headers={"X-Avatar-Id": avatar_id},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_to_expression_hints(text: str, emotion) -> List[dict]:
    hints = []
    text_lower = text.lower()
    if "?" in text:
        hints.append({"at_word": -1, "expression": "thinking", "intensity": 0.6})
    if any(w in text_lower for w in ["haha", "lol", "funny", "laugh"]):
        hints.append({"at_word": 0, "expression": "smile", "intensity": 0.9})
    if emotion.value in ("sadness", "fear"):
        hints.append({"at_word": 0, "expression": "sad", "intensity": 0.7})
    return hints


async def _clear_speaking_state(avatar_id: str, delay: float):
    await asyncio.sleep(delay)
    if avatar_id in _avatar_states:
        _avatar_states[avatar_id]["is_speaking"] = False
