"""
NEUROTWIN OS â€” Orchestrator Agent
Central router that classifies intent and coordinates parallel agent execution.
"""

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Depends
from .learning_agent import learning_agent  # W2
from .decision_engine import DecisionEngine
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .logging_utils import setup_logging
# TraceMiddleware: inline no-op (services.common not in Docker context)
from starlette.middleware.base import BaseHTTPMiddleware
class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)
# get_traced_client: plain httpx.AsyncClient
from contextlib import asynccontextmanager as _acm
@_acm
async def get_traced_client(**kw):
    async with httpx.AsyncClient(**kw) as c:
        yield c
# publish_event: direct redis publish
async def publish_event(channel: str, data: dict, redis_client=None):
    if redis_client:
        import json as _j
        await redis_client.publish(channel, _j.dumps(data))

# Setup structured logging with trace context
setup_logging()

logger = logging.getLogger("orchestrator")

app = FastAPI(title="orchestrator", version="1.0.0")
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
NIM_PROXY_URL = os.getenv("NIM_PROXY_URL", "http://host.docker.internal:8082/v1")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

AGENT_URLS = {
    "emotion": os.getenv("EMOTION_AGENT_URL", "http://perception:8001"),
    "memory": os.getenv("MEMORY_AGENT_URL", "http://memory:8002"),
    "persona": os.getenv("PERSONA_AGENT_URL", "http://agents:8008"),
    "voice": os.getenv("VOICE_AGENT_URL", "http://voice:8006"),
    "behavior": os.getenv("BEHAVIOR_AGENT_URL", "http://behavior:8007"),
    "action": os.getenv("ACTION_AGENT_URL", "http://action:8009"),
    "visual_identity": os.getenv("VISUAL_IDENTITY_URL", "http://visual-identity:8005"),
    "codereview": os.getenv("CODEREVIEW_URL", "http://codereview:8004"),
    "prediction": os.getenv("PREDICTION_URL", "http://prediction:8009"),
}
DIGITAL_TWIN_URL = os.getenv("DIGITAL_TWIN_URL", "http://digital_twin:8014")
decision_engine = DecisionEngine()

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


class UserMessage(BaseModel):
    user_id: str
    session_id: str
    text: str
    voice_mode: bool = False
    context: Dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    type: str
    confidence: float = Field(ge=0.0, le=1.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    needs_voice: bool = False
    needs_action: bool = False


class OrchestrationResult(BaseModel):
    response: str
    avatar_command: Optional[Dict[str, Any]] = None
    visual_state: Optional[Dict[str, Any]] = None
    action_status: Optional[Dict[str, Any]] = None
    voice_audio: Optional[str] = None
    memory_stored: bool = False
    emotion: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


INTENT_PROMPT = """You are an intent classifier for NEUROTWIN AI.
Classify the user message into ONE category:
1. CHAT - General conversation
2. ACTION - Request to perform an action
3. MEMORY_QUERY - Asking about past conversations
4. ANALYTICS - Requesting stats or insights
5. SETTINGS - Configuration or preferences
Return JSON: {"type": "CATEGORY", "confidence": 0.0-1.0, "parameters": {}}
User message: {text}
Classification:"""


async def classify_intent_llm(text: str) -> Intent:
    try:
        async with get_traced_client(timeout=10.0) as client:
            response = await client.post(
                f"{NIM_PROXY_URL}/messages",
                json={
                    "model": "claude-sonnet-4-20250514",
                    "messages": [
                        {"role": "system", "content": INTENT_PROMPT.format(text=text)},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                headers={"Authorization": f"Bearer {ANTHROPIC_API_KEY}"} if ANTHROPIC_API_KEY else {}
            )
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"].strip()
                result = json.loads(content)
                return Intent(**result)
    except Exception as e:
        logger.warning(f"LLM intent classification failed: {e}, falling back to rules")
    return classify_intent_rules(text)


def classify_intent_rules(text: str) -> Intent:
    text_lower = text.lower().strip()
    if any(p in text_lower for p in ["open", "launch", "play", "start", "send", "create", "search", "call", "message", "email", "schedule", "remind", "set"]):
        return Intent(type="ACTION", confidence=0.8, needs_action=True)
    if any(p in text_lower for p in ["remember", "told you", "what did i", "tell me about", "did i mention"]):
        return Intent(type="MEMORY_QUERY", confidence=0.8)
    if any(p in text_lower for p in ["stats", "analytics", "chart", "graph", "insight", "summary", "how many", "show me"]):
        return Intent(type="ANALYTICS", confidence=0.9)
    if any(p in text_lower for p in ["settings", "preferences", "config", "api key", "change", "update"]):
        return Intent(type="SETTINGS", confidence=0.9)
    return Intent(type="CHAT", confidence=0.7)


async def dispatch_agent(agent: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    url = AGENT_URLS.get(agent)
    if not url:
        return {"error": f"Unknown agent: {agent}"}
    try:
        async with get_traced_client(timeout=30.0) as client:
            resp = await client.post(f"{url}/{method}", json=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as e:
        return {"error": f"Agent unreachable: {str(e)}"}
    except httpx.HTTPStatusError as e:
        return {"error": f"Agent error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def publish_redis(channel: str, data: Dict[str, Any]):
    r = await get_redis()
    try:
        await publish_event(channel=channel, data=data, redis_client=r)
        logger.debug(f"Published to {channel}")
    except Exception as e:
        logger.error(f"Redis publish error to {channel}: {e}")


async def fetch_digital_twin_profile(user_id: str) -> dict:
    """Fetch rich digital twin profile from digital_twin service. Graceful fallback."""
    try:
        async with get_traced_client(timeout=3.0) as client:
            resp = await client.get(f"{DIGITAL_TWIN_URL}/profile/{user_id}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Digital twin profile fetch failed: {e}")
    return {}


async def orchestrate_conversation(
    user_id: str,
    session_id: str,
    message: str,
    voice_mode: bool = False,
    context: Optional[Dict[str, Any]] = None
) -> OrchestrationResult:
    context = context or {}

    logger.info(f"Orchestrating message from user {user_id}: {message[:50]}...")
    intent = await classify_intent_llm(message)
    logger.info(f"Intent classified: {intent.type} (conf={intent.confidence:.2f})")

    # â”€â”€ Working Memory: store session goal + intent in Redis (1-hour TTL) â”€â”€
    try:
        _r = await get_redis()
        await _r.setex(f"session:{session_id}:goal", 3600, message[:200])
        await _r.setex(f"session:{session_id}:intent", 3600, intent.type)
        await _r.setex(f"session:{session_id}:user", 3600, user_id)
        logger.debug(f"Working memory saved for session {session_id}")
    except Exception as wm_err:
        logger.warning(f"Working memory write failed: {wm_err}")

    # Parallel tasks (agents + digital twin profile fetched concurrently)
    tasks = [
        ("memory", "log_conversation", {
            "user_id": user_id, "session_id": session_id,
            "content": message, "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"intent": intent.type}
        }),
        ("emotion", "detect_text", {"text": message, "user_id": user_id, "session_id": session_id}),
        ("persona", "get_user_profile", {"user_id": user_id}),
    ]
    # Fetch digital twin profile concurrently with agent tasks
    twin_profile_task = asyncio.create_task(fetch_digital_twin_profile(user_id))

    if intent.type == "ACTION":
        tasks.append(("action", "parse_and_execute", {"text": message, "user_id": user_id}))
    elif intent.type == "MEMORY_QUERY":
        tasks.append(("memory", "search_memories", {"user_id": user_id, "query": message, "limit": 5}))
    elif intent.type == "ANALYTICS":
        tasks.append(("memory", "get_analytics", {"user_id": user_id, "days": context.get("days", 7)}))

    results = {}
    try:
        task_coros = [dispatch_agent(agent, method, params) for agent, method, params in tasks]
        task_results = await asyncio.wait_for(asyncio.gather(*task_coros, return_exceptions=True), timeout=15.0)
        for (agent, method, _), result in zip(tasks, task_results):
            key = f"{agent}.{method}"
            results[key] = {"error": str(result)} if isinstance(result, Exception) else result
    except asyncio.TimeoutError:
        logger.warning("Orchestration timeout â€” proceeding with partial results")
    except Exception as e:
        logger.error(f"Orchestration error: {e}", exc_info=True)

    # Resolve digital twin profile (non-blocking, was running concurrently)
    try:
        twin_profile_data = await asyncio.wait_for(twin_profile_task, timeout=2.0)
    except Exception:
        twin_profile_data = {}

    emotion_data = results.get("emotion.detect_text", {})
    memory_log = results.get("memory.log_conversation", {})
    persona_data = results.get("persona.get_user_profile", {})

    llm_response = ""
    action_result = None
    twin_profile = persona_data

    # Decision engine pre-analysis for CHAT intents
    decision_analysis = None
    if intent.type == "CHAT":
        analysis_context = {
            "emotion": emotion_data.get("dominant", "neutral") if emotion_data else "neutral",
            "intensity": emotion_data.get("intensity", 0.5) if emotion_data else 0.5,
            "time_of_day": datetime.utcnow().hour,
            "intent": intent.type,
            "message": message
        }
        decision_analysis = (await decision_engine.analyze(twin_profile, analysis_context, message)).get("recommended_actions", [])

    if intent.type == "ACTION":
        action_data = results.get("action.parse_and_execute", {})
        if action_data and not action_data.get("error"):
            action_result = action_data
            llm_response = action_data.get("confirmation", f"Executed: {action_data.get('action')}")
    elif intent.type == "MEMORY_QUERY":
        memory_search = results.get("memory.search_memories", {})
        if memory_search and not memory_search.get("error"):
            llm_response = format_memory_query_response(memory_search)
    elif intent.type == "ANALYTICS":
        analytics_data = results.get("memory.get_analytics", {})
        if analytics_data and not analytics_data.get("error"):
            llm_response = format_analytics_response(analytics_data)
    else:
        system_prompt = build_twin_system_prompt(twin_profile_data, persona_data)
        llm_response = await call_llm(message, system_prompt, context)

    # Publish behavior event
    await publish_redis("neurotwin:behavior", {
        "emotion": emotion_data.get("dominant", "neutral") if emotion_data else "neutral",
        "intensity": emotion_data.get("intensity", 0.5) if emotion_data else 0.5,
        "is_speaking": voice_mode or (intent.type not in ["ACTION"]),
        "is_action": intent.type == "ACTION" and bool(action_result),
        "user_id": user_id,
        "session_id": session_id
    })

    # Publish emotion event
    if emotion_data and emotion_data.get("dominant"):
        await publish_redis("neurotwin:emotion", {
            "user_id": user_id,
            "emotion": emotion_data["dominant"],
            "intensity": emotion_data.get("intensity", 0.5),
            "timestamp": datetime.utcnow().isoformat()
        })

    voice_audio_url = None
    if voice_mode and llm_response:
        tts_result = await dispatch_agent("voice", "speak", {
            "text": llm_response, "user_id": user_id, "session_id": session_id
        })
        if tts_result and not tts_result.get("error"):
            voice_audio_url = tts_result.get("audio_url")

    # W2 â€” record pattern for adaptive learning
    ctx_snapshot = {
        "time_of_day": datetime.utcnow().strftime("%H"),
        "emotion": emotion_data.get("dominant", "neutral") if emotion_data else "neutral",
        "intent": intent.type,
    }
    action_taken = intent.type.lower()
    await learning_agent.record_pattern(user_id, ctx_snapshot, action_taken, outcome="neutral")

    return OrchestrationResult(
        response=llm_response,
        visual_state=emotion_data,
        action_status=action_result,
        voice_audio=voice_audio_url,
        memory_stored=bool(memory_log.get("success")),
        emotion=emotion_data,
        metadata={
            "intent": intent.type,
            "confidence": intent.confidence,
            "twin_profile": twin_profile,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def build_default_system_prompt(twin_profile: Dict[str, Any]) -> str:
    base = "You are NEUROTWIN, a warm and empathetic AI companion. "
    if twin_profile:
        traits = twin_profile.get("personality_traits", [])
        if traits:
            base += f"Personality: {', '.join(traits)}. "
        topics = twin_profile.get("interested_topics", [])
        if topics:
            base += f"Topics of interest: {', '.join(topics)}. "
        base += f"Communication style: {twin_profile.get('communication_style', 'supportive and warm')}. "
    base += "Be concise, caring, and adapt your tone to the user's emotional state."
    return base


def build_twin_system_prompt(twin_profile: dict, persona_data: dict) -> str:
    """Build rich LLM system prompt from digital twin profile + persona data."""
    base = "You are NEUROTWIN, a warm and deeply empathetic AI companion. "

    # Identity from digital twin (Phase 4)
    identity = twin_profile.get("identity", {})
    traits = identity.get("traits", [])
    dominant = identity.get("dominant_trait", "")
    if dominant:
        base += f"Your user's dominant personality trait is '{dominant}'. "
    if traits:
        top_traits = [f"{t['name']} ({t['value']:.2f})" for t in traits[:3] if isinstance(t, dict)]
        if top_traits:
            base += f"Personality profile: {', '.join(top_traits)}. "

    # Cognitive state awareness
    cog = twin_profile.get("cognitive_state", {})
    if cog:
        fatigue = float(cog.get("fatigue", 0.2))
        motivation = float(cog.get("motivation", 0.6))
        focus = float(cog.get("focus_level", 0.5))
        if fatigue > 0.7:
            base += "The user appears fatigued — be supportive and concise. "
        elif motivation > 0.75:
            base += "The user is highly motivated right now — match their energy. "
        if focus < 0.35:
            base += "Focus is low — keep responses short and clear. "

    # Prediction context
    prediction = twin_profile.get("prediction", {})
    predicted_action = prediction.get("predicted_action", "")
    if predicted_action and predicted_action != "rest":
        base += f"User may be planning to '{predicted_action}' soon — be relevant. "

    # Fallback to legacy persona data
    if not twin_profile:
        topics = persona_data.get("interested_topics", [])
        if topics:
            base += f"Topics of interest: {', '.join(topics)}. "
        base += f"Communication style: {persona_data.get('communication_style', 'supportive and warm')}. "

    base += "Be concise, caring, and adapt your tone to the user's emotional and cognitive state."
    return base


def format_memory_query_response(memory_data: Dict[str, Any]) -> str:
    memories = memory_data.get("memories", [])
    if not memories:
        return "I don't have any stored memories about that topic yet."
    lines = "\n".join([f"- {m['content'][:100]}..." for m in memories[:3]])
    return f"Here's what I remember:\n{lines}"


def format_analytics_response(analytics_data: Dict[str, Any]) -> str:
    return (f"Your neurotwin statistics:\n"
            f"- Sessions: {analytics_data.get('total_sessions', 0)}\n"
            f"- Messages: {analytics_data.get('total_messages', 0)}\n"
            f"- Engagement: {analytics_data.get('engagement_score', 0) * 100:.0f}%")


async def call_llm(message: str, system_prompt: str, context: Dict[str, Any]) -> str:
    try:
        async with get_traced_client(timeout=30.0) as client:
            response = await client.post(
                f"{NIM_PROXY_URL}/messages",
                json={
                    "model": "claude-sonnet-4-20250514",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                headers={"Authorization": f"Bearer {ANTHROPIC_API_KEY}"} if ANTHROPIC_API_KEY else {}
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return "I'm having trouble connecting right now. Please try again."


@app.post("/v1/orchestrate")
async def orchestrate(request: UserMessage):
    try:
        result = await orchestrate_conversation(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.text,
            voice_mode=request.voice_mode,
            context=request.context
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    try:
        r = await get_redis()
        await r.ping()
        return {"status": "healthy", "service": "orchestrator", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "service": "orchestrator", "error": str(e)}


@app.get("/metrics")
async def metrics():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    global _redis
    try:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        await learning_agent.start(_redis)  # W2 â€” start learning agent
        logger.info("Orchestrator started â€” Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    global _redis
    if _redis:
        await _redis.close()
        logger.info("Orchestrator shutdown â€” Redis closed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8010, reload=True)

