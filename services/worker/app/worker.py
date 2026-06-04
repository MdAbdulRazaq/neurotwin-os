"""
NEUROTWIN OS — ML Worker
Handles batch training jobs, behavior prediction, topic extraction,
memory consolidation, and analytics aggregation.
"""

import asyncio
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as aioredis

from services.common.logging_utils import setup_logging
setup_logging(service_name="neurotwin.worker")
logger = logging.getLogger("neurotwin.worker")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neurotwin:password@localhost:5432/neurotwin_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ── Topic extractor ───────────────────────────────────────────────────────────

class TopicExtractor:
    """
    Lightweight keyword-based topic extraction.
    Production: replace with BERTopic or fine-tuned classifier.
    """

    TOPICS = {
        "work": ["work", "job", "meeting", "boss", "project", "deadline", "office", "career", "colleague"],
        "health": ["health", "exercise", "gym", "sleep", "tired", "sick", "doctor", "mental", "anxious"],
        "relationships": ["friend", "family", "partner", "love", "mom", "dad", "sister", "brother", "date"],
        "learning": ["learn", "study", "book", "course", "read", "skill", "practice", "university"],
        "travel": ["travel", "trip", "flight", "vacation", "hotel", "country", "city", "visit"],
        "food": ["food", "eat", "cook", "restaurant", "coffee", "lunch", "dinner", "breakfast"],
        "technology": ["tech", "code", "software", "computer", "app", "ai", "internet", "phone"],
        "hobbies": ["hobby", "music", "art", "game", "sport", "movie", "film", "creative"],
        "finance": ["money", "budget", "save", "invest", "pay", "salary", "expense", "bank"],
        "goals": ["goal", "plan", "dream", "future", "hope", "achieve", "success", "ambition"],
    }

    def extract(self, text: str) -> List[str]:
        text_lower = text.lower()
        found = []
        for topic, keywords in self.TOPICS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found[:3]  # max 3 topics per message


# ── Analytics aggregator ──────────────────────────────────────────────────────

class AnalyticsAggregator:
    def __init__(self, db_pool: asyncpg.Pool, redis: aioredis.Redis):
        self.db = db_pool
        self.redis = redis
        self.extractor = TopicExtractor()

    async def compute_user_analytics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Compute and cache analytics summary for a user."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get recent messages
        rows = await self.db.fetch(
            """
            SELECT cm.content, cm.role, cm.emotion, cm.created_at, s.id as session_id
            FROM conversation_messages cm
            JOIN sessions s ON cm.session_id = s.id
            WHERE s.user_id = $1 AND cm.created_at > $2
            ORDER BY cm.created_at ASC
            """,
            user_id, since
        )

        messages = [dict(r) for r in rows]
        user_messages = [m for m in messages if m["role"] == "user"]

        # Session stats
        session_ids = list({m["session_id"] for m in messages})
        total_sessions = len(session_ids)
        total_messages = len(user_messages)

        # Avg session length (rough estimate: 5 min per 10 messages)
        avg_session_min = (total_messages / max(total_sessions, 1)) * 0.5

        # Topic frequency
        all_topics: List[str] = []
        for m in user_messages:
            all_topics.extend(self.extractor.extract(m["content"] or ""))
        topic_counts = Counter(all_topics)

        # Mood timeline (hourly buckets)
        mood_timeline = []
        for m in messages:
            if m["emotion"] and m["role"] == "user":
                mood_timeline.append({
                    "timestamp": m["created_at"].isoformat(),
                    "emotion": m["emotion"],
                    "intensity": 0.7,  # fallback; real arousal from perception service
                    "session_id": str(m["session_id"]),
                })

        # Dominant emotion
        emotion_counts = Counter(m["emotion"] for m in messages if m["emotion"])
        dominant = emotion_counts.most_common(1)[0][0] if emotion_counts else "neutral"

        # Engagement score: (messages / days) normalized 0-1
        engagement = min(1.0, (total_messages / max(days, 1)) / 20)

        summary = {
            "user_id": user_id,
            "period_days": days,
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_session_length_minutes": round(avg_session_min, 1),
            "top_topics": [
                {"topic": t, "count": c, "last_mentioned": datetime.now(timezone.utc).isoformat()}
                for t, c in topic_counts.most_common(8)
            ],
            "mood_timeline": mood_timeline[-50:],  # last 50 data points
            "dominant_emotion": dominant,
            "engagement_score": round(engagement, 3),
        }

        # Cache for 15 minutes
        cache_key = f"analytics:{user_id}:{days}"
        await self.redis.setex(cache_key, 900, json.dumps(summary))
        return summary

    async def run_batch_all_users(self):
        """Nightly batch: pre-compute analytics for all active users."""
        user_ids = await self.db.fetch(
            "SELECT DISTINCT user_id FROM sessions WHERE created_at > NOW() - INTERVAL '30 days'"
        )
        logger.info(f"Batch analytics for {len(user_ids)} users")
        for row in user_ids:
            try:
                await self.compute_user_analytics(str(row["user_id"]))
                await asyncio.sleep(0.1)  # rate limit
            except Exception as e:
                logger.error(f"Analytics failed for user {row['user_id']}: {e}")


# ── Memory consolidation ──────────────────────────────────────────────────────

class MemoryConsolidator:
    """
    Consolidates short-term memories into long-term summaries.
    Runs nightly to compress old conversations.
    """

    def __init__(self, db_pool: asyncpg.Pool, redis: aioredis.Redis):
        self.db = db_pool
        self.redis = redis

    async def consolidate_user(self, user_id: str):
        """Summarize conversations older than 7 days into semantic memories."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        old_messages = await self.db.fetch(
            """
            SELECT cm.content, cm.role, s.id as session_id
            FROM conversation_messages cm
            JOIN sessions s ON cm.session_id = s.id
            WHERE s.user_id = $1 AND cm.created_at < $2 AND cm.role = 'user'
            LIMIT 200
            """,
            user_id, cutoff
        )

        if not old_messages:
            return

        # Group by session
        sessions: Dict[str, List[str]] = {}
        for msg in old_messages:
            sid = str(msg["session_id"])
            sessions.setdefault(sid, []).append(msg["content"])

        # Create summary entries
        for sid, msgs in sessions.items():
            combined = " | ".join(msgs[:10])  # take first 10
            summary = combined[:500]  # truncate

            await self.db.execute(
                """
                INSERT INTO memories (user_id, type, summary, created_at)
                VALUES ($1, 'episodic', $2, NOW())
                ON CONFLICT DO NOTHING
                """,
                user_id, summary
            )

        logger.info(f"Consolidated {len(sessions)} sessions for user={user_id}")


# ── Main worker loop ──────────────────────────────────────────────────────────

async def run_worker():
    logger.info("🤖 ML Worker starting…")

    db_pool = await asyncpg.create_pool(
        DATABASE_URL.replace("+asyncpg", ""),
        min_size=2,
        max_size=10,
    )
    redis = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

    aggregator = AnalyticsAggregator(db_pool, redis)
    consolidator = MemoryConsolidator(db_pool, redis)

    logger.info("Worker ready. Starting job loop.")

    while True:
        try:
            hour = datetime.now().hour

            # Batch analytics every hour
            await aggregator.run_batch_all_users()
            logger.info("Analytics batch complete")

            # Memory consolidation at 3AM
            if hour == 3:
                user_ids = await db_pool.fetch(
                    "SELECT DISTINCT id FROM users WHERE is_active = true"
                )
                for row in user_ids:
                    await consolidator.consolidate_user(str(row["id"]))
                logger.info("Memory consolidation complete")

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)

        await asyncio.sleep(3600)  # run hourly


if __name__ == "__main__":
    asyncio.run(run_worker())
