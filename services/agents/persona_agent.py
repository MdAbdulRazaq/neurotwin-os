"""
Persona Agent — Learns user preferences from conversation history.
Writes traits and preferences to Neo4j. Production-ready, no placeholders.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

import redis.asyncio as aioredis

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    from neo4j import AsyncGraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

logger = logging.getLogger("agents.persona")

# ── Configuration ────────────────────────────────────────────────────────────

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://neurotwin:password@postgres:5432/neurotwin_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")

# Simple sentiment word lists
POSITIVE_WORDS = {"great", "good", "awesome", "happy", "love", "nice", "excellent", "excited", "wonderful", "joy"}
NEGATIVE_WORDS = {"bad", "sad", "angry", "hate", "frustrated", "terrible", "awful", "tired", "stressed", "upset"}

# Action keyword → category mapping
ACTION_KEYWORDS = {
    "study": "learning",
    "learn": "learning",
    "read": "learning",
    "work": "productivity",
    "meeting": "productivity",
    "task": "productivity",
    "sleep": "rest",
    "nap": "rest",
    "rest": "rest",
    "exercise": "health",
    "gym": "health",
    "run": "health",
    "eat": "health",
    "play": "entertainment",
    "game": "entertainment",
    "music": "entertainment",
}


class PersonaAgent:
    def __init__(self):
        self.pool = None
        self.neo4j_driver = None
        self.redis = None

    async def start(self):
        if not HAS_ASYNCPG:
            logger.error("asyncpg not installed — PersonaAgent disabled")
            return
        if not HAS_NEO4J:
            logger.error("neo4j driver not installed — PersonaAgent disabled")
            return

        # PostgreSQL pool
        dsn = DB_URL.replace("+asyncpg", "")
        self.pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)

        # Neo4j async driver
        self.neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # Redis
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

        logger.info("PersonaAgent started — PostgreSQL + Neo4j + Redis connected")
        await self._run_loop()

    async def _run_loop(self):
        while True:
            try:
                await self._update_profiles()
            except Exception as e:
                logger.error(f"PersonaAgent update error: {e}", exc_info=True)
            await asyncio.sleep(3600)

    async def _update_profiles(self):
        """
        1. Pull recent user messages from PostgreSQL (last hour).
        2. Infer traits (positive/stressed) and action preferences.
        3. Write to Neo4j:
             (User)-[:HAS_TRAIT {value, timestamp}]->(Trait)
             (User)-[:PREFERS {timestamp}]->(Action)
        """
        if not self.pool or not self.neo4j_driver:
            logger.warning("PersonaAgent: DB not ready, skipping update")
            return

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.user_id, cm.content
                FROM conversation_messages cm
                JOIN sessions s ON cm.session_id = s.id
                WHERE cm.created_at > $1 AND cm.role = 'user'
                """,
                datetime.utcnow() - timedelta(hours=1)
            )

        # Aggregate messages per user
        user_messages: dict[str, list[str]] = {}
        for row in rows:
            uid = str(row["user_id"])
            user_messages.setdefault(uid, []).append(row["content"].lower())

        if not user_messages:
            logger.info("PersonaAgent: no recent messages to process")
            return

        async with self.neo4j_driver.session() as neo4j_session:
            for uid, messages in user_messages.items():
                await self._infer_and_write(neo4j_session, uid, messages)

        logger.info(f"PersonaAgent: updated {len(user_messages)} user profiles in Neo4j")


    async def _infer_and_write(self, session, uid: str, messages: list[str]):
        """Infer traits and preferences, then write to Neo4j."""
        now = datetime.utcnow().isoformat()
        positive = sum(1 for m in messages for w in POSITIVE_WORDS if w in m)
        negative = sum(1 for m in messages for w in NEGATIVE_WORDS if w in m)

        # Determine primary trait
        if positive > negative:
            trait_value = "positive"
        elif negative > positive:
            trait_value = "stressed"
        else:
            trait_value = "neutral"

        # Detect action categories mentioned
        action_counts: dict[str, int] = {}
        for m in messages:
            for keyword, category in ACTION_KEYWORDS.items():
                if keyword in m:
                    action_counts[category] = action_counts.get(category, 0) + 1

        # Merge user node
        await session.run(
            "MERGE (u:User {id: $uid})",
            uid=uid
        )

        # Write trait relationship
        await session.run(
            """
            MERGE (t:Trait {name: $trait})
            WITH t
            MATCH (u:User {id: $uid})
            MERGE (u)-[r:HAS_TRAIT]->(t)
            SET r.value = $trait, r.timestamp = $ts
            """,
            trait=trait_value, uid=uid, ts=now
        )
        logger.debug(f"User {uid} → HAS_TRAIT → {trait_value}")

        # Write preference relationships
        for action_cat, count in action_counts.items():
            await session.run(
                """
                MERGE (a:Action {name: $action})
                WITH a
                MATCH (u:User {id: $uid})
                MERGE (u)-[r:PREFERS]->(a)
                SET r.count = COALESCE(r.count, 0) + $count,
                    r.timestamp = $ts
                """,
                action=action_cat, uid=uid, count=count, ts=now
            )
            logger.debug(f"User {uid} → PREFERS → {action_cat} (count={count})")

        # Cache profile in Redis for fast lookup
        profile = {
            "user_id": uid,
            "trait": trait_value,
            "preferences": list(action_counts.keys()),
            "updated_at": now
        }
        if self.redis:
            await self.redis.setex(f"persona:{uid}:profile", 3600, json.dumps(profile))

    async def stop(self):
        if self.pool:
            await self.pool.close()
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        if self.redis:
            await self.redis.close()


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    agent = PersonaAgent()
    try:
        await agent.start()
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
