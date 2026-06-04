"""
NEUROTWIN OS — Core API Service
Handles conversation orchestration, LLM integration, avatar control, analytics
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.core.config import settings
from app.core.database import init_db, close_db, AsyncSessionLocal
from app.core.redis_client import get_redis
from app.core.memory import MemoryManager, EmbeddingClient, PineconeClient
from app.core.neo4j_client import Neo4jClient
from app.core.llm_client import LLMClient
from app.middleware.auth import JWTMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import auth, convo, avatar, analytics, memory, user
import sys, os
sys.path.insert(0, "/app")
try:
    from services.auth_service.main import router as auth_p12_router
    from services.usage_service.main import router as usage_router
    from services.share_service.main import router as share_router
    from services.analytics_service.main import router as events_router
    from services.analytics_service.referral_service import referral_router
    _p12_loaded = True
except Exception as _e:
    import logging as _l; _l.getLogger("neurotwin.api").warning("Phase 12/13 routers skipped: %s", _e)
    _p12_loaded = False
import uuid
from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware

# ── Logging ──────────────────────────────────────────────────────────────────
setup_logging(service_name="neurotwin.api")
logger = logging.getLogger("neurotwin.api")

# ── Prometheus metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter("api_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Request latency", ["endpoint"])
LLM_CALL_COUNT = Counter("llm_calls_total", "LLM API calls", ["model", "status"])
ACTIVE_WS = Counter("websocket_connections_total", "WebSocket connections opened")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("🧠 NEUROTWIN OS starting up …")
    await init_db()
    redis = await aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    app.state.redis = redis

    # Initialize memory manager
    embed_client = EmbeddingClient()
    neo4j_client = Neo4jClient(
        settings.NEO4J_URI,
        settings.NEO4J_USER,
        settings.NEO4J_PASSWORD.get_secret_value() if settings.NEO4J_PASSWORD else None,
    )
    pinecone_client = PineconeClient()
    app.state.memory_manager = MemoryManager(
        embed_client=embed_client,
        pinecone=pinecone_client,
        redis=redis,
        db_session=AsyncSessionLocal,
        neo4j=neo4j_client,
    )

    logger.info("✅ DB + Redis + Memory connected")
    yield
    await close_db()
    await redis.close()
    await embed_client.close()
    await neo4j_client.close()
    logger.info("🛑 NEUROTWIN OS shut down")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NEUROTWIN OS API",
    description="Multimodal digital-twin companion platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JWTMiddleware, exclude_paths=["/v1/auth", "/health", "/metrics"])
app.add_middleware(RateLimitMiddleware, calls=100, period=60)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    endpoint = request.url.path
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint).observe(latency)
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/v1/auth", tags=["Auth"])
app.include_router(user.router, prefix="/v1/user", tags=["User"])
app.include_router(convo.router, prefix="/v1/conversation", tags=["Conversation"])
app.include_router(avatar.router, prefix="/v1/avatar", tags=["Avatar"])
app.include_router(memory.router, prefix="/v1/memory", tags=["Memory"])
app.include_router(analytics.router, prefix="/v1/analytics", tags=["Analytics"])

# ── Phase 12/13 routers ───────────────────────────────────────────────────────
if _p12_loaded:
    app.include_router(auth_p12_router, tags=["Auth-P12"])
    app.include_router(usage_router,    tags=["Usage"])
    app.include_router(share_router,    tags=["Share"])
    app.include_router(events_router,   tags=["Events"])
    app.include_router(referral_router, tags=["Referral"])


# ── Core endpoints ────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "neurotwin-api", "version": "1.0.0"}


@app.get("/metrics", tags=["System"])
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── WebSocket realtime hub ────────────────────────────────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections keyed by session_id."""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws
        ACTIVE_WS.inc()
        logger.info(f"WS connected: session={session_id}")

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            await ws.send_json(data)

    async def broadcast(self, data: dict):
        for ws in self.active.values():
            await ws.send_json(data)


manager = ConnectionManager()
app.state.ws_manager = manager


@app.websocket("/ws/realtime/{session_id}")
async def ws_realtime(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            event = msg.get("event")

            if event == "ping":
                await websocket.send_json({"event": "pong", "ts": time.time()})

            elif event == "typing":
                # broadcast typing indicator to same session
                await manager.send(session_id, {"event": "typing_ack"})

            elif event == "avatar_ready":
                await manager.send(session_id, {"event": "avatar_ack", "status": "ready"})

            else:
                logger.warning(f"Unknown WS event: {event!r}")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WS disconnected: session={session_id}")
    except Exception as exc:
        logger.error(f"WS error session={session_id}: {exc}")
        manager.disconnect(session_id)
        await websocket.close(code=1011)


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc) if settings.DEBUG else "An error occurred"},
    )
