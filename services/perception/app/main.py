"""
NEUROTWIN OS — Perception Service
Speech-to-text (Deepgram/Whisper), voice emotion detection, audio processing.
"""

import asyncio
import io
import json
import logging
import struct
import wave
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .emotion_model import DistilBERTCNN, load_emotion_model

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware
from services.common.http_client import TracedAsyncClient

setup_logging(service_name="neurotwin.perception")
logger = logging.getLogger("neurotwin.perception")

app = FastAPI(title="neurotwin-perception", version="1.0.0")
app.add_middleware(TraceMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Models ────────────────────────────────────────────────────────────────────

class TranscriptionResult(BaseModel):
    text: str
    confidence: float
    language: str = "en"
    duration_seconds: float
    words: Optional[List[Dict[str, Any]]] = None
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None


class EmotionResult(BaseModel):
    dominant: str
    scores: Dict[str, float]
    arousal: float
    valence: float
    confidence: float


# ── STT Clients ───────────────────────────────────────────────────────────────

class DeepgramSTT:
    """Deepgram Nova-2 streaming and batch STT client."""

    BASE = "https://api.deepgram.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._http = TracedAsyncClient(timeout=60.0)

    async def transcribe(self, audio_bytes: bytes, language: str = "en-US") -> TranscriptionResult:
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }
        params = {
            "model": "nova-2",
            "language": language,
            "smart_format": "true",
            "punctuate": "true",
            "diarize": "false",
            "words": "true",
            "utterances": "true",
        }
        resp = await self._http.post(
            f"{self.BASE}/listen",
            headers=headers,
            params=params,
            content=audio_bytes,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", {})
        channels = results.get("channels", [{}])
        alternatives = channels[0].get("alternatives", [{}])
        best = alternatives[0] if alternatives else {}

        return TranscriptionResult(
            text=best.get("transcript", ""),
            confidence=best.get("confidence", 0.0),
            language=language,
            duration_seconds=data.get("metadata", {}).get("duration", 0.0),
            words=best.get("words", []),
        )

    async def close(self):
        await self._http.aclose()


class WhisperSTT:
    """OpenAI Whisper API client."""

    BASE = "https://api.openai.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._http = TracedAsyncClient(timeout=60.0)

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> TranscriptionResult:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": "whisper-1", "response_format": "verbose_json"}
        if language:
            data["language"] = language[:2]

        resp = await self._http.post(
            f"{self.BASE}/audio/transcriptions",
            headers=headers,
            files=files,
            data=data,
        )
        resp.raise_for_status()
        result = resp.json()

        return TranscriptionResult(
            text=result.get("text", ""),
            confidence=0.95,  # Whisper doesn't return confidence
            language=result.get("language", "en"),
            duration_seconds=result.get("duration", 0.0),
        )

    async def close(self):
        await self._http.aclose()


# ── Text Emotion Detector (DistilBERT-CNN Fusion) ───────────────────────────────────────────────────-

class TextEmotionDetector:
    """Text-based emotion detector using DistilBERT-CNN fusion model."""

    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise"]
    AROUSAL_MAP = {"angry": 0.8, "disgust": 0.5, "fear": 0.7, "happy": 0.9,
                   "sad": 0.2, "surprise": 0.8}
    VALENCE_MAP = {"angry": 0.1, "disgust": 0.1, "fear": 0.1, "happy": 0.9,
                   "sad": 0.1, "surprise": 0.6}

    def __init__(self):
        self.model: Optional[DistilBERTCNN] = None

    def _ensure_model(self):
        """Lazy-load the model on first use."""
        if self.model is None:
            self.model = load_emotion_model()

    def detect_text(self, text: str) -> EmotionResult:
        """Detect emotion from transcribed text."""
        if not text or not text.strip():
            return EmotionResult(
                dominant="neutral",
                scores={e: 0.0 for e in self.EMOTIONS},
                arousal=0.5,
                valence=0.5,
                confidence=0.0,
            )

        try:
            self._ensure_model()
            dominant, probs = self.model.predict(text)

            # Build scores dict
            scores = dict(zip(self.EMOTIONS, probs.tolist()))

            # Normalize to sum to 1
            total = sum(scores.values())
            if total > 0:
                scores = {k: v / total for k, v in scores.items()}

            # Compute arousal/valence from weighted average
            arousal = sum(self.AROUSAL_MAP[e] * scores[e] for e in self.EMOTIONS)
            valence = sum(self.VALENCE_MAP[e] * scores[e] for e in self.EMOTIONS)
            confidence = float(scores.get(dominant, 0.0))

            return EmotionResult(
                dominant=dominant,
                scores=scores,
                arousal=round(arousal, 3),
                valence=round(valence, 3),
                confidence=round(confidence, 3),
            )
        except Exception as e:
            logger.error(f"Text emotion detection error: {e}")
            return EmotionResult(
                dominant="neutral",
                scores={e: 1.0 / len(self.EMOTIONS) for e in self.EMOTIONS},
                arousal=0.5,
                valence=0.5,
                confidence=0.5,
            )


# ── Service instances ─────────────────────────────────────────────────────────
import os
_stt: Optional[Any] = None
_emotion_detector = TextEmotionDetector()

DEEPGRAM_KEY = os.getenv("DEEPGRAM_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

if DEEPGRAM_KEY:
    _stt = DeepgramSTT(DEEPGRAM_KEY)
elif OPENAI_KEY:
    _stt = WhisperSTT(OPENAI_KEY)


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "perception", "stt_available": _stt is not None}


@app.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    detect_emotion: bool = Form(True),
):
    """Transcribe uploaded audio file with optional emotion detection."""
    if not _stt:
        raise HTTPException(status_code=503, detail="STT service not configured")

    audio_bytes = await audio.read()
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25MB limit
        raise HTTPException(status_code=413, detail="Audio file too large (max 25MB)")

    result = await _stt.transcribe(audio_bytes, language)

    if detect_emotion:
        if result.text and result.text.strip():
            emotion = _emotion_detector.detect_text(result.text)
            result.emotion = emotion.dominant
            result.emotion_confidence = emotion.confidence
        else:
            result.emotion = "neutral"
            result.emotion_confidence = 0.0

    return result


@app.post("/emotion", response_model=EmotionResult)
async def detect_emotion(audio: UploadFile = File(...)):
    """Detect emotion from audio without transcription."""
    audio_bytes = await audio.read()

    if not _stt:
        return EmotionResult(
            dominant="neutral",
            scores={e: 1.0 / len(TextEmotionDetector.EMOTIONS) for e in TextEmotionDetector.EMOTIONS},
            arousal=0.5,
            valence=0.5,
            confidence=0.0
        )

    try:
        result = await _stt.transcribe(audio_bytes)
        if result.text and result.text.strip():
            return _emotion_detector.detect_text(result.text)
    except Exception as e:
        logger.error(f"STT transcription failed in emotion detection: {e}")

    return EmotionResult(
        dominant="neutral",
        scores={e: 1.0 / len(TextEmotionDetector.EMOTIONS) for e in TextEmotionDetector.EMOTIONS},
        arousal=0.5,
        valence=0.5,
        confidence=0.0
    )


@app.post("/v1/emotion/analyze", response_model=EmotionResult)
async def analyze_emotion(request: dict):
    """Analyze emotion from text."""
    text = request.get("text", "")
    return _emotion_detector.detect_text(text)


@app.websocket("/ws/stream/{session_id}")
async def ws_stream_transcription(websocket: WebSocket, session_id: str):
    """
    Real-time streaming transcription via WebSocket.
    Client sends raw audio chunks; server responds with partial transcripts.
    """
    await websocket.accept()
    logger.info(f"Streaming STT session started: {session_id}")
    buffer = bytearray()
    CHUNK_SIZE = 16000 * 2  # 1 second at 16kHz 16-bit

    try:
        while True:
            chunk = await asyncio.wait_for(websocket.receive_bytes(), timeout=30.0)
            buffer.extend(chunk)

            if len(buffer) >= CHUNK_SIZE:
                audio_segment = bytes(buffer)
                buffer.clear()

                # Always compute emotion from any available transcribed text (local, no API cost)
                emotion = _emotion_detector.detect_text("")

                # If STT is available, include transcript
                if _stt:
                    try:
                        result = await _stt.transcribe(audio_segment)
                        # Compute emotion from transcribed text (accurate)
                        emotion = _emotion_detector.detect_text(result.text or "")
                        await websocket.send_json({
                            "type": "transcript",
                            "text": result.text,
                            "confidence": result.confidence,
                            "emotion": emotion.dominant,
                            "emotion_confidence": emotion.confidence,
                            "arousal": emotion.arousal,
                            "valence": emotion.valence,
                            "is_final": False,
                        })
                        continue
                    except Exception as e:
                        logger.warning(f"Streaming transcription error: {e}")

                # STT unavailable or transcription failed → send emotion-only
                await websocket.send_json({
                    "type": "transcript",  # keep same type for frontend compatibility
                    "text": "",
                    "emotion": emotion.dominant,
                    "emotion_confidence": emotion.confidence,
                    "arousal": emotion.arousal,
                    "valence": emotion.valence,
                    "is_final": False,
                })

    except asyncio.TimeoutError:
        # Send final transcript
        if buffer and _stt:
            try:
                result = await _stt.transcribe(bytes(buffer))
                final_emotion = _emotion_detector.detect_text(result.text or "")
                await websocket.send_json({
                    "type": "transcript",
                    "text": result.text,
                    "emotion": final_emotion.dominant,
                    "emotion_confidence": final_emotion.confidence,
                    "arousal": final_emotion.arousal,
                    "valence": final_emotion.valence,
                    "is_final": True,
                })
            except Exception:
                pass
        await websocket.close()
    except WebSocketDisconnect:
        logger.info(f"Streaming STT session ended: {session_id}")
    except Exception as e:
        logger.error(f"WS STT error: {e}")
        await websocket.close(code=1011)
