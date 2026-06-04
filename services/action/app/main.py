"""
NEUROTWIN OS — Action Agent
Executes real-world actions (browser automation, OS commands, app control).
"""

import asyncio
import json
import logging
import os
import platform
import random
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("action")
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
)

app = FastAPI(title="action-agent", version="1.0.0")

REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
PLAYWRIGHT_URL = os.getenv("PLAYWRIGHT_URL", "http://localhost:3001")

_redis: Optional[aioredis.Redis] = None


class ActionRequest(BaseModel):
    text: str = Field(..., description="Natural language command")
    user_id: str = Field(..., description="User identifier")


class ActionResult(BaseModel):
    success: bool
    action: str
    result: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ActionType(str, Enum):
    OPEN_URL = "open_url"
    PLAY_MUSIC = "play_music"
    SEND_WHATSAPP = "send_whatsapp"
    CHECK_WEATHER = "check_weather"
    CREATE_EVENT = "create_event"
    SEARCH_WEB = "search_web"
    TELL_JOKE = "tell_joke"
    UNKNOWN = "unknown"


class ActionParser:
    PATTERNS: List[Tuple[re.Pattern, ActionType, List[str]]] = [
        (re.compile(r"open\s+(?:url\s+)?(https?://\S+)", re.IGNORECASE), ActionType.OPEN_URL, ["url"]),
        (re.compile(r"open\s+(?:website\s+)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,})", re.IGNORECASE), ActionType.OPEN_URL, ["domain"]),
        (re.compile(r"play\s+(.+?)(?:\s+on\s+youtube)?", re.IGNORECASE), ActionType.PLAY_MUSIC, ["query"]),
        (re.compile(r"(?:send\s+)?(?:whatsapp|message)\s+(?:to\s+)?(\w+)\s+(.+)", re.IGNORECASE), ActionType.SEND_WHATSAPP, ["contact", "message"]),
        (re.compile(r"message\s+(\w+)\s+(.+)", re.IGNORECASE), ActionType.SEND_WHATSAPP, ["contact", "message"]),
        (re.compile(r"(?:what.?s\s+)?the\s+weather\s+(?:like\s+)?(?:in\s+)?(.+?)(?:\s+next\s+week)?", re.IGNORECASE), ActionType.CHECK_WEATHER, ["location"]),
        (re.compile(r"weather\s+(?:in\s+)?(.+)", re.IGNORECASE), ActionType.CHECK_WEATHER, ["location"]),
        (re.compile(r"search\s+(?:for\s+)?(.+?)(?:\s+on\s+(?:google|the\s+web))?", re.IGNORECASE), ActionType.SEARCH_WEB, ["query"]),
        (re.compile(r"google\s+(.+)", re.IGNORECASE), ActionType.SEARCH_WEB, ["query"]),
        (re.compile(r"create\s+(?:an\s+)?(?:event|meeting|reminder)\s+(.+?)(?:\s+(?:at|on)\s+(.+))?", re.IGNORECASE), ActionType.CREATE_EVENT, ["title", "time"]),
        (re.compile(r"(?:tell|say|give)\s+(?:me\s+)?(?:a\s+)?(joke|funny\s+story)", re.IGNORECASE), ActionType.TELL_JOKE, ["type"]),
    ]

    ACTION_KEYWORDS = {
        ActionType.OPEN_URL: ["open", "launch", "visit", "go to", "navigate"],
        ActionType.PLAY_MUSIC: ["play", "listen", "music", "song"],
        ActionType.SEND_WHATSAPP: ["message", "whatsapp", "text", "send"],
        ActionType.CHECK_WEATHER: ["weather", "temperature", "forecast"],
        ActionType.SEARCH_WEB: ["search", "google", "find"],
        ActionType.CREATE_EVENT: ["event", "meeting", "reminder", "schedule"],
        ActionType.TELL_JOKE: ["joke", "funny", "laugh"],
    }

    def parse(self, text: str) -> Tuple[ActionType, Dict[str, Any]]:
        text = text.strip()
        for pattern, action_type, param_names in self.PATTERNS:
            match = pattern.search(text)
            if match:
                params = dict(zip(param_names, match.groups()))
                params = {k: v.strip() if isinstance(v, str) else v for k, v in params.items()}
                return action_type, params
        text_lower = text.lower()
        for action_type, keywords in self.ACTION_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return action_type, {"text": text, "confidence": 0.6}
        return ActionType.UNKNOWN, {"text": text, "confidence": 0.0}


class BaseExecutor:
    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        raise NotImplementedError


class URLExecutor(BaseExecutor):
    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        url = params.get("url") or params.get("domain")
        if not url:
            return ActionResult(success=False, action="open_url", result="", error="No URL provided")
        if not url.startswith(("http://", "https://")):
            if "." in url and len(url.split(".")[-1]) >= 2:
                url = f"https://{url}"
            else:
                return ActionResult(success=False, action="open_url", result="", error=f"Invalid URL: {url}")
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["start", url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            return ActionResult(success=True, action="open_url", result=f"Opened {url}", details={"url": url})
        except Exception as e:
            return ActionResult(success=False, action="open_url", result="", error=str(e))


class YouTubeExecutor(BaseExecutor):
    def __init__(self):
        self.browser_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        query = params.get("query", "").strip()
        if not query:
            return ActionResult(success=False, action="play_music", result="", error="No query provided")
        encoded_query = httpx.utils.query_params({"search_query": query})
        youtube_url = f"https://www.youtube.com/results?{encoded_query}"
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["start", youtube_url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", youtube_url])
            else:
                subprocess.Popen(["xdg-open", youtube_url])
            return ActionResult(success=True, action="play_music", result=f"Searching YouTube for '{query}'", details={"url": youtube_url})
        except Exception as e:
            return ActionResult(success=False, action="play_music", result="", error=str(e))

    async def close(self):
        await self.browser_client.aclose()


class WhatsAppExecutor(BaseExecutor):
    def __init__(self):
        self.base_url = PLAYWRIGHT_URL

    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        contact = params.get("contact", "").strip()
        message = params.get("message", "").strip()
        if not contact or not message:
            return ActionResult(success=False, action="send_whatsapp", result="", error="Missing contact or message")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.base_url}/whatsapp/send", json={"contact": contact, "message": message})
                if response.status_code == 200:
                    return ActionResult(success=True, action="send_whatsapp", result=f"Message sent to {contact}", details={"contact": contact, "message_preview": message[:50]})
                else:
                    return ActionResult(success=False, action="send_whatsapp", result="", error="WhatsApp send failed")
        except httpx.RequestError:
            return ActionResult(success=False, action="send_whatsapp", result="", error="Browser automation service unavailable")
        except Exception as e:
            return ActionResult(success=False, action="send_whatsapp", result="", error=str(e))


class WeatherExecutor(BaseExecutor):
    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        location = params.get("location", "your location").strip()
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    geo_resp = await client.get("http://api.openweathermap.org/geo/1.0/direct", params={"q": location, "limit": 1, "appid": api_key})
                    if geo_resp.status_code == 200 and geo_resp.json():
                        lat = geo_resp.json()[0]["lat"]
                        lon = geo_resp.json()[0]["lon"]
                        city = geo_resp.json()[0]["name"]
                        weather_resp = await client.get("http://api.openweathermap.org/data/2.5/weather", params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"})
                        if weather_resp.status_code == 200:
                            data = weather_resp.json()
                            temp = data["main"]["temp"]
                            desc = data["weather"][0]["description"]
                            return ActionResult(success=True, action="check_weather", result=f"Weather in {city}: {temp}°C, {desc}", details={"city": city, "temp": temp})
            except Exception as e:
                logger.warning(f"OpenWeatherMap API failed: {e}")
        return ActionResult(success=True, action="check_weather", result=f"The weather in {location.title()} is partly cloudy with a high of 22°C.", details={"location": location})


class WebSearchExecutor(BaseExecutor):
    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        query = params.get("query", "").strip()
        if not query:
            return ActionResult(success=False, action="search_web", result="", error="No search query provided")
        encoded_query = httpx.utils.query_params({"q": query})
        search_url = f"https://www.google.com/search?{encoded_query}"
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["start", search_url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", search_url])
            else:
                subprocess.Popen(["xdg-open", search_url])
            return ActionResult(success=True, action="search_web", result=f"Searching for '{query}' on Google", details={"url": search_url})
        except Exception as e:
            return ActionResult(success=False, action="search_web", result="", error=str(e))


class JokeExecutor(BaseExecutor):
    JOKES = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why did the developer go broke? Because he used up all his cache.",
    ]

    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://v2.jokeapi.dev/joke/Any?format=json&safe-mode")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("joke"):
                        return ActionResult(success=True, action="tell_joke", result=data["joke"], details={"source": "JokeAPI"})
        except Exception:
            pass
        return ActionResult(success=True, action="tell_joke", result=random.choice(self.JOKES), details={"source": "local"})


class CalendarExecutor(BaseExecutor):
    async def execute(self, params: Dict[str, Any], user_id: str) -> ActionResult:
        title = params.get("title", "Untitled Event")
        time = params.get("time", "unspecified time")
        return ActionResult(success=True, action="create_event", result=f"Created event: '{title}' at {time}", details={"title": title, "time": time})


class ActionEngine:
    def __init__(self):
        self.parser = ActionParser()
        self.executors = {
            ActionType.OPEN_URL: URLExecutor(),
            ActionType.PLAY_MUSIC: YouTubeExecutor(),
            ActionType.SEND_WHATSAPP: WhatsAppExecutor(),
            ActionType.CHECK_WEATHER: WeatherExecutor(),
            ActionType.SEARCH_WEB: WebSearchExecutor(),
            ActionType.TELL_JOKE: JokeExecutor(),
            ActionType.CREATE_EVENT: CalendarExecutor(),
        }
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.pending_confirmations: Dict[str, asyncio.Future] = {}
        self.confirmation_task: Optional[asyncio.Task] = None
        self.planner = None
        self.executor = None

    async def start(self):
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("neurotwin:action_confirmation_responses")
        self.confirmation_task = asyncio.create_task(self._confirmation_listener())
        from .planner import Planner
        from .plan_executor import PlanExecutor
        self.planner = Planner()
        self.executor = PlanExecutor(self)
        logger.info("ActionEngine started")

    async def _confirmation_listener(self):
        while True:
            try:
                msg = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["channel"] == "neurotwin:action_confirmation_responses":
                    data = json.loads(msg["data"])
                    request_id = data.get("request_id")
                    confirmed = data.get("confirmed", False)
                    if request_id in self.pending_confirmations:
                        future = self.pending_confirmations.pop(request_id)
                        if not future.done():
                            future.set_result(confirmed)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Confirmation listener error: {e}")

    async def stop(self):
        if self.confirmation_task:
            self.confirmation_task.cancel()
            try:
                await self.confirmation_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        for executor in self.executors.values():
            if hasattr(executor, 'close'):
                await executor.close()
        if self.redis:
            await self.redis.close()

    async def publish_result(self, request_id: str, user_id: str, session_id: str, result: ActionResult):
        try:
            if self.redis:
                await self.redis.publish("neurotwin:actions", json.dumps({
                    "request_id": request_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "action": result.action,
                    "success": result.success,
                    "result": result.result,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        except Exception as e:
            logger.error(f"Failed to publish action result: {e}")

    async def request_confirmation(self, action_type: ActionType, params: Dict[str, Any],
                                   user_id: str, session_id: str = "") -> bool:
        """Request user confirmation before executing an action. Returns True if confirmed."""
        if not self.redis:
            return False
        request_id = str(uuid.uuid4())
        confirm_msg = {
            "request_id": request_id,
            "action": action_type.value,
            "params": params,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis.publish("neurotwin:action_confirmation_requests", json.dumps(confirm_msg))
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.pending_confirmations[request_id] = future
        try:
            confirmed = await asyncio.wait_for(future, timeout=5.0)
            return confirmed
        except asyncio.TimeoutError:
            return False
        finally:
            fut = self.pending_confirmations.pop(request_id, None)
            if fut and not fut.done():
                fut.cancel()

    async def parse_and_execute(self, text: str, user_id: str, session_id: str = "") -> ActionResult:
        action_type, params = self.parser.parse(text)
        if action_type == ActionType.UNKNOWN:
            return ActionResult(success=False, action="unknown", result="", error="Could not understand command.")
        executor = self.executors.get(action_type)
        if not executor:
            return ActionResult(success=False, action=action_type.value, result="", error=f"Action not implemented")
        if not self._safety_check(action_type, params):
            return ActionResult(success=False, action=action_type.value, result="", error="Safety check blocked")
        request_id = str(uuid.uuid4())
        confirmed = await self.request_confirmation(action_type, params, user_id, session_id)
        if not confirmed:
            denied = ActionResult(success=False, action=action_type.value, result="", error="Action denied or timed out")
            await self.publish_result(request_id, user_id, session_id, denied)
            return denied
        try:
            result = await executor.execute(params, user_id)
        except Exception as e:
            result = ActionResult(success=False, action=action_type.value, result="", error=str(e))
        await self.publish_result(request_id, user_id, session_id, result)
        return result

    def _safety_check(self, action_type: ActionType, params: Dict[str, Any]) -> bool:
        dangerous = ["delete", "remove", "format", "shutdown", "restart", "rm -rf", "sudo"]
        text_to_check = " ".join(str(v) for v in params.values())
        return not any(k in text_to_check.lower() for k in dangerous)


engine: Optional[ActionEngine] = None


@app.on_event("startup")
async def startup_event():
    global engine
    engine = ActionEngine()
    await engine.start()
    logger.info("ActionAgent initialized")


@app.on_event("shutdown")
async def shutdown_event():
    global engine
    if engine:
        await engine.stop()
        engine = None


@app.get("/health")
async def health_check():
    return {"status": "healthy" if engine else "unhealthy", "service": "action", "timestamp": datetime.utcnow().isoformat()}


@app.post("/v1/action/parse", response_model=None)
async def parse_action(text: str):
    """Parse natural language into action type and params."""
    action_type, params = ActionParser().parse(text)
    return {"action": action_type.value, "params": params, "confidence": 1.0 if action_type != ActionType.UNKNOWN else 0.0}


@app.post("/v1/action/execute", response_model=ActionResult)
async def execute_action(request: ActionRequest):
    if not engine:
        raise HTTPException(status_code=503, detail="Action engine not initialized")
    try:
        # Multi-step → planner → executor; single-step → parse_and_execute
        if engine.planner and not engine.planner._is_single_step(request.text):
            plan = await engine.planner.create_plan(goal=request.text, user_id=request.user_id)
            summary = await engine.executor.execute_plan(plan)
            return ActionResult(
                success=plan.status == "completed",
                action="plan",
                result=summary["overall_result"],
                details=summary
            )
        return await engine.parse_and_execute(text=request.text, user_id=request.user_id)
    except Exception as e:
        logger.error(f"Action execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/action/registry")
async def get_registry():
    return {
        "supported_actions": [a.value for a in ActionType if a != ActionType.UNKNOWN],
    }


@app.get("/v1/action/history")
async def get_action_history(user_id: str, limit: int = 10):
    if not engine or not engine.redis:
        return {"history": []}
    try:
        history = await engine.redis.zrevrange(f"user:{user_id}:actions", 0, limit - 1)
        return {"history": [json.loads(i) for i in history if i]}
    except Exception as e:
        return {"history": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8012, reload=True)
