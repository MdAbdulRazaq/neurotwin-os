"""
NEUROTWIN OS — Memory Service
Hybrid memory: short-term (Redis), semantic (Pinecone), structured (Postgres), graph (Neo4j).
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
import uuid

from app.core.config import settings
from app.core.database import (
    Memory as DBMemory,
    ConversationMessage as DBMessage,
    EmotionEvent as DBEmotionEvent,
    Session as DBSession,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.neo4j_client import Neo4jClient
logger = logging.getLogger("neurotwin.memory")


class MemoryType(str, Enum):
    EPISODIC = "episodic"       # specific events / conversations
    SEMANTIC = "semantic"       # facts and knowledge
    EMOTIONAL = "emotional"     # emotional moments
    PREFERENCE = "preference"   # user preferences
    RELATIONSHIP = "relationship"  # people / places / topics


@dataclass
class MemoryChunk:
    id: str
    user_id: str
    type: MemoryType
    summary: str
    raw_text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0  # 0.0–1.0

    def to_pinecone_vector(self) -> dict:
        return {
            "id": self.id,
            "values": self.embedding,
            "metadata": {
                "user_id": self.user_id,
                "type": self.type.value,
                "summary": self.summary[:500],  # Pinecone metadata limit
                "timestamp": self.timestamp,
                "importance": self.importance,
                **self.metadata,
            },
        }


class EmbeddingClient:
    """OpenAI Embeddings or local sentence-transformers fallback."""

    OPENAI_BASE = "https://api.openai.com/v1"

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Returns list of embeddings for a batch of texts."""
        if settings.OPENAI_API_KEY:
            return await self._openai_embed(texts)
        return self._local_embed(texts)

    async def embed_one(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]

    async def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": settings.EMBEDDING_MODEL}
        resp = await self._http.post(f"{self.OPENAI_BASE}/embeddings", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]

    def _local_embed(self, texts: List[str]) -> List[List[float]]:
        """Fallback: deterministic hash-based pseudo-embedding (dev only)."""
        logger.warning("Using deterministic fallback embeddings — not for production!")
        results = []
        dim = settings.EMBEDDING_DIMENSIONS
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            seed = int.from_bytes(h[:4], "big")
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(dim).tolist()
            results.append(vec)
        return results

    async def close(self):
        await self._http.aclose()


class PineconeClient:
    """Thin async wrapper around Pinecone REST API v1."""

    BASE = "https://api.pinecone.io"

    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Api-Key": settings.PINECONE_API_KEY.get_secret_value() if settings.PINECONE_API_KEY else "",
                "Content-Type": "application/json",
            },
        )
        self.index = settings.PINECONE_INDEX_NAME

    def _ns(self, user_id: str) -> str:
        return f"user_{user_id}"

    async def upsert(self, user_id: str, vectors: List[dict]):
        url = f"{self.BASE}/indexes/{self.index}/vectors/upsert"
        payload = {"vectors": vectors, "namespace": self._ns(user_id)}
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def query(
        self,
        user_id: str,
        vector: List[float],
        top_k: int = 8,
        filter: Optional[dict] = None,
    ) -> List[dict]:
        url = f"{self.BASE}/indexes/{self.index}/vectors/query"
        payload = {
            "vector": vector,
            "topK": top_k,
            "namespace": self._ns(user_id),
            "includeMetadata": True,
        }
        if filter:
            payload["filter"] = filter
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        return resp.json().get("matches", [])

    async def delete_vectors(self, user_id: str, ids: List[str]):
        """Delete specific vectors from the user's namespace."""
        url = f"{self.BASE}/indexes/{self.index}/vectors/delete"
        payload = {"ids": ids, "namespace": self._ns(user_id)}
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()

    async def delete_user(self, user_id: str):
        """GDPR: delete all vectors for a user (right to erasure)."""
        url = f"{self.BASE}/indexes/{self.index}/vectors/delete"
        payload = {"deleteAll": True, "namespace": self._ns(user_id)}
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()

    async def close(self):
        await self._http.aclose()


class MemoryManager:
    """
    High-level memory interface used by Conversation service.
    Handles storage, retrieval, summarization, importance scoring.
    """

    SHORT_TERM_WINDOW = 20  # messages to keep in Redis short-term

    def __init__(self, embed_client: EmbeddingClient, pinecone: PineconeClient, redis, db_session, neo4j=None):
        self.embed = embed_client
        self.pinecone = pinecone
        self.redis = redis
        self.db = db_session
        self.neo4j = neo4j

    # ── Store ─────────────────────────────────────────────────────────────────

    async def store_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        text: str,
        emotion: Optional[str] = None,
        emotion_source: Optional[str] = None,
        emotion_intensity: Optional[float] = None,
        arousal: Optional[float] = None,
        valence: Optional[float] = None,
        metadata: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """Persist message to short-term (Redis) + semantic memory (Pinecone)."""
        msg_id = f"{session_id}_{int(time.time() * 1000)}"

        # Short-term: append to Redis list
        short_key = f"st:{user_id}:{session_id}"
        entry = json.dumps({
            "id": msg_id,
            "role": role,
            "text": text,
            "ts": time.time(),
            "emotion": emotion,
            "emotion_source": emotion_source,
            "emotion_intensity": emotion_intensity,
            "arousal": arousal,
            "valence": valence,
        })
        await self.redis.rpush(short_key, entry)
        await self.redis.ltrim(short_key, -self.SHORT_TERM_WINDOW, -1)
        await self.redis.expire(short_key, settings.REDIS_TTL * 24)

        # Neo4j graph: create message node + update twin behavioral profile
        if self.neo4j:
            try:
                await self.neo4j.create_message_node(
                    user_id=user_id, session_id=session_id, role=role,
                    content=text[:500], message_id=msg_id, emotion=emotion,
                )
                if emotion and emotion != "neutral":
                    await self.neo4j.update_emotion_pattern(user_id, emotion)
            except Exception as e:
                logger.warning(f"Neo4j graph write skipped: {e}")

        # Semantic memory (user messages only, skip if Pinecone not configured)
        if role == "user" and settings.PINECONE_API_KEY:
            try:
                summary = self._summarize(text)
                importance = self._score_importance(text, emotion)
                embedding = await self.embed.embed_one(summary)
                chunk = MemoryChunk(
                    id=msg_id,
                    user_id=user_id,
                    type=MemoryType.EPISODIC,
                    summary=summary,
                    raw_text=text,
                    embedding=embedding,
                    metadata={
                        "session_id": session_id,
                        "emotion": emotion or "neutral",
                        "emotion_source": emotion_source or "text",
                        "emotion_intensity": emotion_intensity,
                        "arousal": arousal,
                        "valence": valence,
                        **(metadata or {}),
                    },
                    importance=importance,
                )
                await self.pinecone.upsert(user_id, [chunk.to_pinecone_vector()])
                # Persist to PostgreSQL for long-term storage and listing
                if db is not None:
                    memory_obj = DBMemory(
                        user_id=user_id,
                        type=MemoryType.EPISODIC.value,
                        summary=summary,
                        raw_text=text,
                        pinecone_vector_id=msg_id,
                        importance=importance,
                        emotion=emotion or "neutral",
                        metadata_json={
                            "session_id": session_id,
                            "emotion_source": emotion_source or "text",
                            "emotion_intensity": emotion_intensity,
                            "arousal": arousal,
                            "valence": valence,
                            **(metadata or {}),
                        },
                    )
                    db.add(memory_obj)
            except Exception as e:
                logger.warning(f"Semantic memory store skipped: {e}")

        # Persist conversation message to PostgreSQL for analytics (always)
        if db is not None:
            try:
                db_message = DBMessage(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                    role=role,
                    content=text,
                    emotion=emotion,
                )
                db.add(db_message)

                db_session = await db.get(
                    DBSession,
                    uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                )
                if db_session is not None:
                    db_session.message_count = (db_session.message_count or 0) + 1
            except Exception as e:
                logger.warning(f"Failed to persist message to conversation_messages: {e}")

            # Persist emotion event if emotion provided
            if emotion:
                try:
                    emotion_event = DBEmotionEvent(
                        id=uuid.uuid4(),
                        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
                        session_id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                        emotion=emotion,
                        intensity=float(emotion_intensity if emotion_intensity is not None else 0.5),
                        arousal=float(arousal if arousal is not None else 0.5),
                        valence=float(valence if valence is not None else 0.5),
                        source=(emotion_source or "text")[:20],
                    )
                    db.add(emotion_event)
                except Exception as e:
                    logger.warning(f"Failed to persist emotion event: {e}")

        return msg_id

    # ── Retrieve ──────────────────────────────────────────────────────────────

    async def get_short_term(self, user_id: str, session_id: str) -> List[dict]:
        """Get recent messages from Redis."""
        short_key = f"st:{user_id}:{session_id}"
        raw_list = await self.redis.lrange(short_key, 0, -1)
        if raw_list:
            return [json.loads(r) for r in raw_list]

        hydrated = await self._hydrate_short_term_from_db(user_id, session_id)
        if hydrated:
            await self._write_short_term_cache(user_id, session_id, hydrated)
        return hydrated

    async def get_semantic(self, user_id: str, query_text: str, top_k: int = 8) -> List[str]:
        """Retrieve semantically relevant memories as context strings."""
        if not settings.PINECONE_API_KEY:
            return []
        try:
            embedding = await self.embed.embed_one(query_text)
            matches = await self.pinecone.query(user_id, embedding, top_k=top_k)
            contexts = []
            for m in matches:
                meta = m.get("metadata", {})
                score = m.get("score", 0)
                if score > 0.75:
                    contexts.append(meta.get("summary", ""))
            return [c for c in contexts if c]
        except Exception as e:
            logger.warning(f"Semantic memory retrieval skipped: {e}")
            return []

    async def get_context_for_prompt(
        self, user_id: str, session_id: str, user_message: str
    ) -> tuple[List[dict], List[str]]:
        """Returns (short_term_messages, semantic_context_strings) for prompt building."""
        short_term = await self.get_short_term(user_id, session_id)
        semantic = await self.get_semantic(user_id, user_message)
        return short_term, semantic

    # ── Privacy ───────────────────────────────────────────────────────────────

    async def forget_user(self, user_id: str):
        """GDPR right-to-erasure: wipe all memory for user."""
        await self.pinecone.delete_user(user_id)
        # Redis: scan and delete user keys
        async for key in self.redis.scan_iter(f"st:{user_id}:*"):
            await self.redis.delete(key)
        logger.info(f"GDPR forget completed for user={user_id}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _summarize(self, text: str) -> str:
        """Simple extractive summarization (replace with LLM summarizer in prod)."""
        words = text.split()
        if len(words) <= 30:
            return text
        return " ".join(words[:30]) + "…"

    def _score_importance(self, text: str, emotion: Optional[str]) -> float:
        """Heuristic importance scoring 0–1."""
        score = 0.5
        high_value_keywords = ["remember", "important", "never forget", "always", "my name", "birthday", "love", "hate", "work", "family"]
        text_lower = text.lower()
        for kw in high_value_keywords:
            if kw in text_lower:
                score = min(score + 0.1, 1.0)
        if emotion in ("sadness", "anger", "joy"):
            score = min(score + 0.15, 1.0)
        return round(score, 2)

    async def _hydrate_short_term_from_db(self, user_id: str, session_id: str) -> List[dict]:
        """
        Recover recent session history from PostgreSQL when Redis is empty.
        This keeps the prompt memory stable across API/Redis restarts.
        """
        async with self.db() as db:
            stmt = (
                select(DBMessage)
                .join(DBSession, DBMessage.session_id == DBSession.id)
                .where(
                    DBSession.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id),
                    DBSession.id == (uuid.UUID(session_id) if isinstance(session_id, str) else session_id),
                )
                .order_by(DBMessage.created_at.desc())
                .limit(self.SHORT_TERM_WINDOW)
            )
            result = await db.execute(stmt)
            messages = list(reversed(result.scalars().all()))

        return [
            {
                "id": str(message.id),
                "role": message.role,
                "text": message.content,
                "ts": message.created_at.timestamp(),
                "emotion": message.emotion,
                "emotion_source": None,
                "emotion_intensity": None,
                "arousal": None,
                "valence": None,
            }
            for message in messages
        ]

    async def _write_short_term_cache(self, user_id: str, session_id: str, entries: List[dict]) -> None:
        """Warm Redis short-term memory with recovered conversation history."""
        if not entries:
            return

        short_key = f"st:{user_id}:{session_id}"
        payload = [json.dumps(entry) for entry in entries[-self.SHORT_TERM_WINDOW:]]
        await self.redis.delete(short_key)
        await self.redis.rpush(short_key, *payload)
        await self.redis.expire(short_key, settings.REDIS_TTL * 24)
