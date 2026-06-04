"""
NEUROTWIN OS — Behavior Agent
Finite State Machine for avatar behavior coordination.

Subscribes to: neurotwin:emotions, neurotwin:voice, neurotwin:avatar_control
Publishes to: neurotwin:avatar_state

State transitions driven by real-time events from multiple sources.
"""

import asyncio
import json
import logging
import os
import random
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware
from services.common.redis_events import publish_event

setup_logging(service_name="neurotwin.behavior")
logger = logging.getLogger("neurotwin.behavior")

app = FastAPI(title="behavior-agent", version="1.0.0")
app.add_middleware(TraceMiddleware)

# ── State Machine Definition ───────────────────────────────────────────────────

class AvatarState(Enum):
    """Avatar behavioral states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EMOTING = "emoting"
    ACTION = "action"
    PRE_SPEAKING = "pre_speaking"


@dataclass
class BehaviorContext:
    """Complete behavior state context."""
    # Current FSM state
    current_state: AvatarState = AvatarState.IDLE
    state_since: float = 0.0

    # Emotion data
    current_emotion: str = "neutral"
    emotion_intensity: float = 0.5
    emotion_since: float = 0.0

    # Voice state
    is_speaking: bool = False
    is_listening: bool = False
    voice_activity: float = 0.0  # 0-1 amplitude

    # Action state
    is_action: bool = False
    action_type: Optional[str] = None

    # Blendshape targets (0-1 normalized)
    target_blendshapes: Dict[str, float] = field(default_factory=lambda: {
        "eyeBlinkL": 0.0, "eyeBlinkR": 0.0,
        "mouthSmile_L": 0.0, "mouthSmile_R": 0.0,
        "mouthFrown_L": 0.0, "mouthFrown_R": 0.0,
        "browDown_L": 0.0, "browDown_R": 0.0,
        "browInnerUp": 0.0,
        "jawOpen": 0.0,
        "cheekSquint_L": 0.0, "cheekSquint_R": 0.0,
    })

    # Current interpolated blendshapes
    current_blendshapes: Dict[str, float] = field(default_factory=dict)

    # Idle animation state
    idle_breath_phase: float = 0.0
    eye_drift_x: float = 0.0
    eye_drift_y: float = 0.0
    blink_timer: float = 0.0
    next_blink: float = 2.0
    blink_state: float = 0.0  # 0=open, 1=closed

    # Gaze control (normalized -1 to 1)
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    gaze_target_x: float = 0.0
    gaze_target_y: float = 0.0
    gaze_timer: float = 0.0
    gaze_update_interval: float = 2.0  # seconds between saccades

    # Head micro-movement
    head_tilt: float = 0.0
    head_tilt_phase: float = 0.0

    # Hesitation flag
    hesitation_active: bool = False

    def __post_init__(self):
        """Initialize current_blendshapes from target."""
        self.current_blendshapes = self.target_blendshapes.copy()


# ── Temporal Sync Buffer ────────────────────────────────────────────────────────

@dataclass
class BufferedEvent:
    """Event with timestamp for temporal alignment."""
    data: Dict
    timestamp: float
    source: str  # "emotion", "voice", "action"
    ttl: float = 0.5  # Time to live in ms (500ms max)


class TemporalSyncBuffer:
    """200-300ms buffer that aligns emotion, voice, and action events.

    Rules:
    - Buffer window: 200-300ms
    - Stale event threshold: 500ms
    - Priority: speech > strong emotion > action > idle
    """

    def __init__(self, buffer_ms: float = 250, stale_threshold_ms: float = 500):
        self.buffer_duration = buffer_ms / 1000.0
        self.stale_threshold = stale_threshold_ms / 1000.0
        self.emotion_buffer: list[BufferedEvent] = []
        self.voice_buffer: list[BufferedEvent] = []
        self.action_buffer: list[BufferedEvent] = []
        self.last_emotion_ts: float = 0.0
        self.last_voice_ts: float = 0.0
        self.last_action_ts: float = 0.0

    def push(self, source: str, data: Dict, timestamp: float):
        event = BufferedEvent(data=data, timestamp=timestamp, source=source)
        buffer = getattr(self, f"{source}_buffer", None)
        if buffer is not None:
            buffer.append(event)

    def _cleanup_stale(self, current_time: float):
        cutoff = current_time - self.stale_threshold
        for buffer_attr in ['emotion_buffer', 'voice_buffer', 'action_buffer']:
            buffer = getattr(self, buffer_attr)
            setattr(self, buffer_attr, [e for e in buffer if e.timestamp > cutoff])

    def _get_most_recent_in_window(self, buffer: list[BufferedEvent],
                                    current_time: float) -> Optional[BufferedEvent]:
        if not buffer:
            return None
        window_start = current_time - self.buffer_duration
        window_events = [e for e in buffer if e.timestamp >= window_start]
        if not window_events:
            return None
        return max(window_events, key=lambda e: e.timestamp)

    def get_aligned_state(self, current_time: float) -> Dict[str, Optional[BufferedEvent]]:
        self._cleanup_stale(current_time)
        emotion = self._get_most_recent_in_window(self.emotion_buffer, current_time)
        voice = self._get_most_recent_in_window(self.voice_buffer, current_time)
        action = self._get_most_recent_in_window(self.action_buffer, current_time)
        if emotion and emotion.timestamp > self.last_emotion_ts:
            self.last_emotion_ts = emotion.timestamp
        if voice and voice.timestamp > self.last_voice_ts:
            self.last_voice_ts = voice.timestamp
        if action and action.timestamp > self.last_action_ts:
            self.last_action_ts = action.timestamp
        return {"emotion": emotion, "voice": voice, "action": action}

    def get_priority_state(self, aligned: Dict[str, Optional[BufferedEvent]]) -> str:
        voice = aligned.get("voice")
        emotion = aligned.get("emotion")
        action = aligned.get("action")
        if voice and (voice.data.get("is_speaking") or voice.data.get("event") == "speech_start"):
            return "speech"
        if emotion and emotion.data.get("intensity", 0) >= 0.7:
            return "strong_emotion"
        if action:
            return "action"
        return "idle"


# ── State Transition Rules ────────────────────────────────────────────────────

class StateTransition:
    """Defines allowed state transitions and their conditions."""
    IDLE_TRANSITIONS = {
        "voice_listen_start": AvatarState.LISTENING,
        "thinking_start": AvatarState.THINKING,
        "speaking_start": AvatarState.SPEAKING,
        "emotion_high": AvatarState.EMOTING,
        "action_start": AvatarState.ACTION,
    }
    LISTENING_TRANSITIONS = {
        "voice_listen_stop": AvatarState.THINKING,
        "emotion_high": AvatarState.EMOTING,
        "action_start": AvatarState.ACTION,
    }
    THINKING_TRANSITIONS = {
        "speaking_start": AvatarState.SPEAKING,
        "emotion_high": AvatarState.EMOTING,
        "action_start": AvatarState.ACTION,
        "timeout": AvatarState.IDLE,
    }
    SPEAKING_TRANSITIONS = {
        "speaking_stop": AvatarState.IDLE,
        "emotion_high": AvatarState.EMOTING,
        "action_start": AvatarState.ACTION,
    }
    EMOTING_TRANSITIONS = {
        "emotion_done": AvatarState.IDLE,
        "action_start": AvatarState.ACTION,
        "speaking_start": AvatarState.SPEAKING,
    }
    ACTION_TRANSITIONS = {
        "action_done": AvatarState.IDLE,
        "emotion_high": AvatarState.EMOTING,
    }
    PRE_SPEAKING_TRANSITIONS = {
        "speech_start": AvatarState.SPEAKING,
        "timeout": AvatarState.IDLE,
    }

    @classmethod
    def get_allowed(cls, current: AvatarState) -> Dict[str, AvatarState]:
        return getattr(cls, f"{current.name}_TRANSITIONS", {})


# ── Emotion → Blendshape Mapping ───────────────────────────────────────────────

EMOTION_BLENDSHAPES = {
    "joy": {"mouthSmile_L": 0.8, "mouthSmile_R": 0.8, "browInnerUp": 0.3, "cheekSquint_L": 0.2, "cheekSquint_R": 0.2, "eyeBlinkL": 0.0, "eyeBlinkR": 0.0},
    "sadness": {"mouthFrown_L": 0.6, "mouthFrown_R": 0.6, "browDown_L": 0.4, "browDown_R": 0.4, "browInnerUp": 0.2, "eyeBlinkL": 0.3, "eyeBlinkR": 0.3},
    "anger": {"browDown_L": 0.8, "browDown_R": 0.8, "browInnerUp": 0.1, "mouthFrown_L": 0.4, "mouthFrown_R": 0.4, "cheekSquint_L": 0.3, "cheekSquint_R": 0.3},
    "surprise": {"jawOpen": 0.7, "browUp_L": 0.6, "browUp_R": 0.6, "eyeWide_L": 0.4, "eyeWide_R": 0.4, "mouthSmile_L": 0.1, "mouthSmile_R": 0.1},
    "fear": {"browDown_L": 0.3, "browDown_R": 0.3, "browInnerUp": 0.6, "jawOpen": 0.4, "mouthFrown_L": 0.2, "mouthFrown_R": 0.2},
    "disgust": {"browDown_L": 0.5, "browDown_R": 0.5, "noseSneer_L": 0.6, "noseSneer_R": 0.6, "mouthFrown_L": 0.3, "mouthFrown_R": 0.3},
    "neutral": {"mouthSmile_L": 0.1, "mouthSmile_R": 0.1, "browDown_L": 0.0, "browDown_R": 0.0, "jawOpen": 0.0},
}

VISEME_MAP = {
    "sil": {},
    "aa": {"jawOpen": 0.7, "mouthSmile_L": 0.1, "mouthSmile_R": 0.1},
    "ee": {"jawOpen": 0.4, "mouthSmile_L": 0.6, "mouthSmile_R": 0.6},
    "ih": {"jawOpen": 0.3, "mouthSmile_L": 0.2, "mouthSmile_R": 0.2},
    "oh": {"jawOpen": 0.5, "mouthSmile_L": 0.3, "mouthSmile_R": 0.3},
    "uu": {"jawOpen": 0.4, "mouthSmile_L": 0.0, "mouthSmile_R": 0.0},
    "th": {"jawOpen": 0.2, "mouthFrown_L": 0.4, "mouthFrown_R": 0.4},
    "ff": {"jawOpen": 0.0, "mouthSmile_L": 0.3, "mouthSmile_R": 0.3},
    "pp": {"jawOpen": 0.0, "mouthSmile_L": 0.2, "mouthSmile_R": 0.2},
    "ss": {"jawOpen": 0.1, "mouthFrown_L": 0.3, "mouthFrown_R": 0.3},
}


# ── Behavior Engine ────────────────────────────────────────────────────────────

class BehaviorEngine:
    """Finite State Machine for avatar behavior."""

    def __init__(self):
        self.ctx = BehaviorContext()
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.running = False
        self.update_task: Optional[asyncio.Task] = None

        # Temporal Sync Buffer
        self.temporal_buffer = TemporalSyncBuffer(buffer_ms=250, stale_threshold_ms=500)

        # Timers for auto-transitions
        self.transition_delays = {
            AvatarState.LISTENING: 0.5,
            AvatarState.THINKING: 2.0,
            AvatarState.SPEAKING: 0.5,
            AvatarState.EMOTING: 2.0,
            AvatarState.PRE_SPEAKING: 0.15,  # pre-speech anticipation (150ms)
        }

        # Current active timers
        self.active_timers: Dict[AvatarState, asyncio.Task] = {}

        # Thinking delay (300-800ms after transcript)
        self.thinking_delay_until: float = 0.0
        self.thinking_delay_active: bool = False

        # Head movement phase
        self.head_tilt_phase: float = 0.0

    async def start(self):
        """Start the behavior agent."""
        redis_url = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
        self.redis = await aioredis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("neurotwin:emotion", "neurotwin:voice", "neurotwin:avatar_control")
        logger.info("BehaviorAgent subscribed to neurotwin:emotions, neurotwin:voice, neurotwin:avatar_control")
        self.running = True
        asyncio.create_task(self._listen_emotions())
        asyncio.create_task(self._listen_voice())
        asyncio.create_task(self._listen_control())
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info("BehaviorEngine started")

    async def stop(self):
        """Stop the behavior agent."""
        self.running = False
        for timer in self.active_timers.values():
            timer.cancel()
        self.active_timers.clear()
        if self.update_task:
            self.update_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis:
            await self.redis.close()
        logger.info("BehaviorEngine stopped")

    # ── Event Handlers ────────────────────────────────────────────────────────

    async def _listen_emotions(self):
        while self.running:
            try:
                msg = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if msg and msg["channel"] == "neurotwin:emotion":
                    try:
                        data = json.loads(msg["data"])
                        await self._on_emotion(data)
                    except json.JSONDecodeError:
                        logger.warning("Invalid emotion message")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Emotion listener error: {e}")
                await asyncio.sleep(0.1)

    async def _on_emotion(self, data: Dict):
        """Handle emotion event - push to temporal buffer."""
        emotion = data.get("emotion", "neutral").lower()
        intensity = float(data.get("intensity", 0.5))
        user_id = data.get("user_id")
        logger.debug(f"Emotion buffered: {emotion} (intensity={intensity:.2f})")
        current_time = asyncio.get_event_loop().time()
        self.temporal_buffer.push("emotion", data, current_time)

    async def _listen_voice(self):
        while self.running:
            try:
                msg = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if msg and msg["channel"] == "neurotwin:voice":
                    try:
                        data = json.loads(msg["data"])
                        event = data.get("event", "")
                        if event == "listening" or data.get("listening"):
                            self._on_listening_start()
                        elif event == "transcript" or data.get("transcript"):
                            self._on_transcript()
                        elif event == "speech_start" or data.get("speaking"):
                            self._on_speaking_start()
                        elif event == "speech_end":
                            self._on_speaking_stop()
                        elif event == "pre_speech" or data.get("pre_speech"):
                            self._on_pre_speech()
                    except json.JSONDecodeError:
                        logger.warning("Invalid voice message")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Voice listener error: {e}")
                await asyncio.sleep(0.1)

    def _on_listening_start(self):
        """User started speaking/listening - push to buffer."""
        data = {"event": "listening", "is_listening": True, "voice_activity": 1.0}
        current_time = asyncio.get_event_loop().time()
        self.temporal_buffer.push("voice", data, current_time)
        logger.debug("Voice buffered: listening start")

    def _on_transcript(self):
        """Transcript received - start thinking delay."""
        self.ctx.is_listening = False
        self.ctx.voice_activity = 0.0
        logger.debug("Voice event: transcript - starting thinking delay")
        # Cancel LISTENING auto-transition timer
        self._cancel_timer(AvatarState.LISTENING)
        # Start thinking delay (300-800ms)
        self.thinking_delay_active = True
        self.thinking_delay_until = asyncio.get_event_loop().time() + random.uniform(0.3, 0.8)

    def _on_speaking_start(self):
        """AI started speaking - push to buffer."""
        data = {"event": "speech_start", "is_speaking": True}
        current_time = asyncio.get_event_loop().time()
        self.temporal_buffer.push("voice", data, current_time)
        logger.debug("Voice buffered: speech start")

    def _on_speaking_stop(self):
        """AI finished speaking - push to buffer."""
        data = {"event": "speech_end", "is_speaking": False}
        current_time = asyncio.get_event_loop().time()
        self.temporal_buffer.push("voice", data, current_time)
        logger.debug("Voice buffered: speech stop")

    def _on_pre_speech(self):
        """Handle pre-speech anticipation signal."""
        logger.debug("Voice event: pre_speech - entering PRE_SPEAKING")
        # Random hesitation: 10% chance
        self.ctx.hesitation_active = (random.random() < 0.1)
        self.transition_to(AvatarState.PRE_SPEAKING)

    async def _listen_control(self):
        while self.running:
            try:
                msg = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if msg and msg["channel"] == "neurotwin:avatar_control":
                    try:
                        data = json.loads(msg["data"])
                        await self._on_control(data)
                    except json.JSONDecodeError:
                        logger.warning("Invalid control message")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Control listener error: {e}")
                await asyncio.sleep(0.1)

    async def _on_control(self, data: Dict):
        """Handle direct control command - push to buffer."""
        action_type = data.get("action_type", "unknown")
        current_time = asyncio.get_event_loop().time()
        self.temporal_buffer.push("action", data, current_time)
        logger.debug(f"Action buffered: {action_type}")
        blendshapes = data.get("blendshapes", {})
        if blendshapes:
            for key, value in blendshapes.items():
                if key in self.ctx.target_blendshapes:
                    self.ctx.target_blendshapes[key] = max(0.0, min(1.0, float(value)))

    # ── State Machine ───────────────────────────────────────────────────────────

    def transition_to(self, new_state: AvatarState):
        """Transition to new state with validation."""
        old_state = self.ctx.current_state
        allowed = StateTransition.get_allowed(old_state)

        if new_state == old_state:
            self._cancel_timer(old_state)
            self._start_timer(old_state)
            return

        # Fixed validation: check if new_state is in allowed values
        if new_state not in allowed.values():
            logger.warning(f"Invalid transition: {old_state.value} → {new_state.value}")
            logger.warning(f"Allowed: {[s.value for s in allowed.values()]}")
            return

        logger.info(f"State transition: {old_state.value} → {new_state.value}")
        self.ctx.current_state = new_state
        self.ctx.state_since = asyncio.get_event_loop().time()

        # Cancel old state timer
        self._cancel_timer(old_state)

        # Setup new state
        self._setup_state(new_state)

        # Start timer for auto-transition if needed
        if new_state in self.transition_delays:
            self._start_timer(new_state)

    def _setup_state(self, state: AvatarState):
        """Setup target blendshapes for a state."""
        # Reset hesitation when leaving PRE_SPEAKING
        if state != AvatarState.PRE_SPEAKING:
            self.ctx.hesitation_active = False

        if state == AvatarState.IDLE:
            self.ctx.target_blendshapes.update({
                "eyeBlinkL": 0.0, "eyeBlinkR": 0.0,
                "mouthSmile_L": 0.1, "mouthSmile_R": 0.1,
                "browDown_L": 0.0, "browDown_R": 0.0,
                "jawOpen": 0.0,
            })
        elif state == AvatarState.LISTENING:
            self.ctx.target_blendshapes.update({
                "eyeBlinkL": 0.0, "eyeBlinkR": 0.0,
                "mouthSmile_L": 0.0, "mouthSmile_R": 0.0,
                "browDown_L": 0.1, "browDown_R": 0.1,
                "jawOpen": 0.05,
            })
        elif state == AvatarState.THINKING:
            self.ctx.target_blendshapes.update({
                "eyeBlinkL": 0.0, "eyeBlinkR": 0.0,
                "mouthSmile_L": 0.0, "mouthSmile_R": 0.0,
                "browDown_L": 0.3, "browDown_R": 0.3,
                "browInnerUp": 0.2,
                "jawOpen": 0.05,
            })
        elif state == AvatarState.SPEAKING:
            self.ctx.target_blendshapes.update({
                "jawOpen": 0.3,
                "mouthSmile_L": 0.1, "mouthSmile_R": 0.1,
            })
        elif state == AvatarState.EMOTING:
            emotion = self.ctx.current_emotion
            if emotion in EMOTION_BLENDSHAPES:
                for key, value in EMOTION_BLENDSHAPES[emotion].items():
                    if key in self.ctx.target_blendshapes:
                        self.ctx.target_blendshapes[key] = value
        elif state == AvatarState.PRE_SPEAKING:
            # Anticipation pose: slight smile, attentive eyebrows
            self.ctx.target_blendshapes.update({
                "mouthSmile_L": 0.2, "mouthSmile_R": 0.2,
                "browInnerUp": 0.3,
                "jawOpen": 0.0,
            })

    def _start_timer(self, state: AvatarState):
        delay = self.transition_delays.get(state, 5.0)
        self.active_timers[state] = asyncio.create_task(self._state_timer(state, delay))

    def _cancel_timer(self, state: AvatarState):
        if state in self.active_timers:
            self.active_timers[state].cancel()
            del self.active_timers[state]

    def _cancel_delays(self):
        """Cancel any active micro-behavior delays."""
        self.thinking_delay_active = False
        self.hesitation_active = False

    async def _state_timer(self, state: AvatarState, delay: float):
        try:
            await asyncio.sleep(delay)
            self._on_state_timeout(state)
        except asyncio.CancelledError:
            pass

    def _on_state_timeout(self, state: AvatarState):
        if self.ctx.current_state == state:
            logger.info(f"State {state.value} timeout - transitioning")
            if state == AvatarState.EMOTING:
                self.transition_to(AvatarState.IDLE)
            elif state == AvatarState.THINKING:
                self.transition_to(AvatarState.SPEAKING if self.ctx.is_speaking else AvatarState.IDLE)
            elif state == AvatarState.SPEAKING:
                self.transition_to(AvatarState.IDLE)
            elif state == AvatarState.LISTENING:
                self.transition_to(AvatarState.THINKING)
            elif state == AvatarState.PRE_SPEAKING:
                self.transition_to(AvatarState.IDLE)

    # ── Update Loop ─────────────────────────────────────────────────────────────

    async def _update_loop(self):
        loop = asyncio.get_event_loop()
        target_fps = 30
        dt = 1.0 / target_fps

        while self.running:
            try:
                current_time = loop.time()
                self.ctx.state_duration = current_time - self.ctx.state_since

                # Process state transitions
                self._check_transitions()

                # Update idle animations
                self._update_idle_animations(dt)

                # Update blink cycle
                self._update_blink(dt)

                # Update head micro-movements
                self._update_head_movement(dt)

                # Update gaze movement
                self._update_gaze_movement(dt)

                # Interpolate blendshapes smoothly
                self._interpolate_blendshapes(dt)

                # Publish current state to Redis
                await self._publish_state()

                # Sleep to maintain 30 FPS
                await asyncio.sleep(dt)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Update loop error: {e}")
                await asyncio.sleep(dt)

    def _check_transitions(self):
        """Check conditional transitions using temporal alignment and micro-behaviors."""
        current_time = asyncio.get_event_loop().time()
        aligned = self.temporal_buffer.get_aligned_state(current_time)

        # Process aligned emotion
        emotion_event = aligned.get("emotion")
        if emotion_event:
            data = emotion_event.data
            self.ctx.current_emotion = data.get("emotion", "neutral")
            self.ctx.emotion_intensity = float(data.get("intensity", 0.5))
            self.ctx.emotion_since = emotion_event.timestamp

        # Process aligned voice
        voice_event = aligned.get("voice")
        if voice_event:
            data = voice_event.data
            event_type = data.get("event", "")
            if event_type == "listening":
                self.ctx.is_listening = True
                self.ctx.voice_activity = 1.0
            elif event_type == "transcript":
                self.ctx.is_listening = False
                self.ctx.voice_activity = 0.0
            elif event_type == "speech_start":
                self.ctx.is_speaking = True
            elif event_type == "speech_end":
                self.ctx.is_speaking = False

        # Process aligned action
        action_event = aligned.get("action")
        if action_event:
            self.ctx.is_action = True
            self.ctx.action_type = action_event.data.get("action_type")
        else:
            self.ctx.is_action = False
            self.ctx.action_type = None

        # Check thinking delay expiry
        if self.thinking_delay_active and current_time >= self.thinking_delay_until:
            self.thinking_delay_active = False
            if self.ctx.current_state != AvatarState.THINKING:
                self.transition_to(AvatarState.THINKING)

        # Determine priority from core signals
        priority = self.temporal_buffer.get_priority_state(aligned)

        # High-priority transitions
        if priority == "speech" and self.ctx.is_speaking:
            self.thinking_delay_active = False  # Cancel any pending thinking delay
            if self.ctx.current_state != AvatarState.SPEAKING:
                self.transition_to(AvatarState.SPEAKING)
            return
        elif priority == "strong_emotion":
            self.thinking_delay_active = False
            if self.ctx.current_state != AvatarState.EMOTING:
                self.transition_to(AvatarState.EMOTING)
            return
        elif priority == "action":
            self.thinking_delay_active = False
            if self.ctx.current_state != AvatarState.ACTION:
                self.transition_to(AvatarState.ACTION)
            return

        # Lower-priority voice-driven state: LISTENING (interruptible)
        if voice_event:
            event_type = voice_event.data.get("event")
            if event_type == "listening":
                self.thinking_delay_active = False
                if self.ctx.current_state != AvatarState.LISTENING:
                    self.transition_to(AvatarState.LISTENING)
                return
            # transcript handled via thinking delay

    def _update_idle_animations(self, dt: float):
        """Update idle breathing, eye drift, and decay other movements when not idle."""
        current_time = asyncio.get_event_loop().time()
        if self.ctx.current_state != AvatarState.IDLE:
            self.ctx.eye_drift_x *= 0.95
            self.ctx.eye_drift_y *= 0.95
            self.ctx.gaze_x *= 0.95
            self.ctx.gaze_y *= 0.95
            self.ctx.head_tilt *= 0.9
            return

        # Breathing cycle
        self.ctx.idle_breath_phase += dt * 1.5
        breath = 0.02 * (1 + 0.3 * self.ctx.idle_breath_phase % (2 * 3.14159))

        # Eye drift
        drift_speed = 0.5
        self.ctx.eye_drift_x += dt * drift_speed * (current_time % 1 - 0.5) * 0.1
        self.ctx.eye_drift_y += dt * drift_speed * (current_time % 1 - 0.5) * 0.1
        self.ctx.eye_drift_x = max(-0.03, min(0.03, self.ctx.eye_drift_x))
        self.ctx.eye_drift_y = max(-0.03, min(0.03, self.ctx.eye_drift_y))

    def _update_blink(self, dt: float):
        """Update natural blinking."""
        self.ctx.blink_timer += dt
        if self.ctx.blink_timer >= self.ctx.next_blink:
            self.ctx.blink_state = 1.0
            self.ctx.blink_timer = 0.0
            self.ctx.next_blink = 2.0 + asyncio.get_event_loop().time() % 3.0
        elif self.ctx.blink_timer >= 0.15 and self.ctx.blink_state > 0:
            self.ctx.blink_state = 0.0
        if self.ctx.current_state in (AvatarState.IDLE, AvatarState.THINKING, AvatarState.SPEAKING):
            self.ctx.target_blendshapes["eyeBlinkL"] = self.ctx.blink_state
            self.ctx.target_blendshapes["eyeBlinkR"] = self.ctx.blink_state

    def _update_head_movement(self, dt: float):
        """Update subtle head micro-movements (nods, tilts)."""
        self.head_tilt_phase += dt * 1.5  # 1.5 Hz base frequency
        if self.ctx.current_state in (AvatarState.SPEAKING, AvatarState.LISTENING, AvatarState.THINKING):
            self.ctx.head_tilt = 0.05 * (0.5 + 0.5 * math.sin(self.head_tilt_phase))
        else:
            self.ctx.head_tilt *= 0.9

    def _update_gaze_movement(self, dt: float):
        """Update gaze saccades."""
        self.ctx.gaze_timer += dt
        if self.ctx.gaze_timer >= self.ctx.gaze_update_interval:
            self.ctx.gaze_timer = 0.0
            self.ctx.gaze_target_x = random.uniform(-0.4, 0.4)
            self.ctx.gaze_target_y = random.uniform(-0.3, 0.3)
        speed = 2.0  # units per second
        self.ctx.gaze_x += (self.ctx.gaze_target_x - self.ctx.gaze_x) * dt * speed
        self.ctx.gaze_y += (self.ctx.gaze_target_y - self.ctx.gaze_y) * dt * speed

    def _interpolate_blendshapes(self, dt: float):
        """Smooth interpolation to target values."""
        lerp_factor = min(dt * 8.0, 1.0)
        for key in self.ctx.target_blendshapes:
            current = self.ctx.current_blendshapes.get(key, 0.0)
            target = self.ctx.target_blendshapes[key]
            if key == "jawOpen" and self.ctx.current_state == AvatarState.SPEAKING:
                target *= (0.85 + 0.15 * abs((self.ctx.state_duration * 3) % (2 * 3.14159)))
            new_value = current + (target - current) * lerp_factor
            self.ctx.current_blendshapes[key] = new_value

    async def _publish_state(self):
        """Publish current behavior state to Redis."""
        try:
            state_data = {
                "state": self.ctx.current_state.value,
                "emotion": self.ctx.current_emotion,
                "emotion_intensity": self.ctx.emotion_intensity,
                "is_speaking": self.ctx.is_speaking,
                "is_listening": self.ctx.is_listening,
                "blendshapes": {k: round(v, 4) for k, v in self.ctx.current_blendshapes.items()},
                "state_duration": round(self.ctx.state_duration, 3),
                "timestamp": datetime.utcnow().isoformat(),
                # Micro-behavior data
                "gaze": {"x": round(self.ctx.gaze_x, 4), "y": round(self.ctx.gaze_y, 4)},
                "head_tilt": round(self.ctx.head_tilt, 4),
                "hesitation": self.ctx.hesitation_active,
            }
            await publish_event(
                channel="neurotwin:avatar_state",
                data=state_data,
                redis_client=self.redis
            )
        except Exception as e:
            logger.error(f"Failed to publish state: {e}")

    # ── API Endpoints ───────────────────────────────────────────────────────────

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "behavior",
            "state": behavior_engine.ctx.current_state.value if behavior_engine else "uninitialized",
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.get("/v1/behavior/state")
    async def get_state():
        ctx = behavior_engine.ctx if behavior_engine else BehaviorContext()
        return {
            "state": ctx.current_state.value,
            "emotion": ctx.current_emotion,
            "emotion_intensity": ctx.emotion_intensity,
            "is_speaking": ctx.is_speaking,
            "is_listening": ctx.is_listening,
            "blendshapes": ctx.current_blendshapes,
            "state_duration": ctx.state_duration,
        }

    @app.post("/v1/behavior/state")
    async def set_state(
        emotion: str = "neutral",
        intensity: float = 0.5,
        is_speaking: bool = None,
        is_action: bool = None
    ):
        if behavior_engine:
            behavior_engine.ctx.current_emotion = emotion.lower()
            behavior_engine.ctx.emotion_intensity = max(0.0, min(1.0, intensity))
            if is_speaking is not None:
                behavior_engine.ctx.is_speaking = is_speaking
            if is_action is not None:
                behavior_engine.ctx.is_action = is_action
            if is_speaking:
                target_state = AvatarState.SPEAKING
            elif behavior_engine.ctx.is_action:
                target_state = AvatarState.ACTION
            elif intensity >= 0.6:
                target_state = AvatarState.EMOTING
            else:
                target_state = AvatarState.IDLE
            behavior_engine.transition_to(target_state)
            return {
                "success": True,
                "state": behavior_engine.ctx.current_state.value,
                "emotion": behavior_engine.ctx.current_emotion
            }
        return {"success": False, "error": "Engine not initialized"}

    @app.get("/v1/behavior/emotion")
    async def get_emotion():
        return {
            "emotion": behavior_engine.ctx.current_emotion if behavior_engine else "neutral",
            "intensity": behavior_engine.ctx.emotion_intensity if behavior_engine else 0.5
        }

# ── Global Engine Instance ────────────────────────────────────────────────────

behavior_engine: Optional[BehaviorEngine] = None

@app.on_event("startup")
async def startup_event():
    global behavior_engine
    try:
        behavior_engine = BehaviorEngine()
        await behavior_engine.start()
        logger.info("BehaviorAgent started successfully")
    except Exception as e:
        logger.error(f"BehaviorAgent startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global behavior_engine
    if behavior_engine:
        await behavior_engine.stop()
        behavior_engine = None
        logger.info("BehaviorAgent shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8007, reload=True)
