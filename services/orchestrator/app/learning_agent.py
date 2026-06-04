"""
learning_agent.py — Adaptive learning for NEUROTWIN OS.
Records BehaviorPatterns → Neo4j (User)-[:PERFORMED]->(Action).
Mirrors weights to Redis. Adaptive weight = f(count, acceptance_rate).
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger("learning_agent")

REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
FLUSH_INTERVAL = 60


@dataclass
class BehaviorPattern:
    user_id: str
    time_of_day: str
    emotion: str
    action: str
    count: int = 0
    accepted: int = 0
    rejected: int = 0
    last_seen: float = field(default_factory=time.time)
    habit_score: float = 0.0  # New: habit formation metric

    @property
    def acceptance_rate(self) -> float:
        total = self.accepted + self.rejected
        return self.accepted / total if total > 0 else 0.5

    @property
    def weight(self) -> float:
        base = 0.5 + min(0.3, self.count * 0.02)
        return round(base + (self.acceptance_rate - 0.5) * 0.4, 4)


class LearningAgent:
    def __init__(self):
        self._patterns: dict[str, BehaviorPattern] = {}
        self._redis: Optional[aioredis.Redis] = None
        self._running = False

    async def start(self, redis_client: aioredis.Redis):
        self._redis = redis_client
        self._running = True
        asyncio.create_task(self._flush_loop())
        logger.info("LearningAgent started")

    def _key(self, user_id: str, time_of_day: str, emotion: str, action: str) -> str:
        return f"{user_id}:{time_of_day}:{emotion}:{action}"

    async def record_pattern(
        self,
        user_id: str,
        ctx: dict,
        action: str,
        outcome: str = "neutral",
    ) -> None:
        """Call after every orchestrator response. outcome: accept|reject|neutral"""
        tod = ctx.get("time_of_day", "unknown")
        emotion = ctx.get("emotion", "neutral")
        k = self._key(user_id, tod, emotion, action)

        if k not in self._patterns:
            self._patterns[k] = BehaviorPattern(
                user_id=user_id, time_of_day=tod, emotion=emotion, action=action
            )
        p = self._patterns[k]
        p.count += 1
        p.last_seen = time.time()
        if outcome == "accept":
            p.accepted += 1
        elif outcome == "reject":
            p.rejected += 1

        if self._redis:
            try:
                await self._redis.hset(
                    "neurotwin:patterns",
                    k,
                    json.dumps({"weight": p.weight, "count": p.count, "action": action}),
                )
            except Exception as e:
                logger.warning(f"Redis pattern write failed: {e}")


    async def get_learned_weights(self, user_id: str) -> dict:
        if not self._redis:
            return {}
        try:
            all_patterns = await self._redis.hgetall("neurotwin:patterns")
            weights = {}
            for k, v in all_patterns.items():
                if k.startswith(user_id + ":"):
                    data = json.loads(v)
                    weights[data["action"]] = data["weight"]
            return weights
        except Exception:
            return {}

    async def _flush_loop(self):
        while self._running:
            await asyncio.sleep(FLUSH_INTERVAL)
            await self._flush_to_neo4j()

    async def _flush_to_neo4j(self):
        if not self._patterns:
            return
        try:
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
            async with driver.session() as session:
                for p in list(self._patterns.values()):
                    await session.run(
                        """
                        MERGE (u:User {id: $uid})
                        MERGE (a:Action {name: $action})
                        MERGE (u)-[r:PERFORMED]->(a)
                        SET r.count = $count,
                            r.acceptance_rate = $ar,
                            r.weight = $weight,
                            r.last_seen = $ts
                        """,
                        uid=p.user_id, action=p.action, count=p.count,
                        ar=p.acceptance_rate, weight=p.weight,
                        ts=p.last_seen,
                    )
            await driver.close()
            logger.info(f"Flushed {len(self._patterns)} patterns to Neo4j")
        except Exception as e:
            logger.warning(f"Neo4j flush failed (non-critical): {e}")


learning_agent = LearningAgent()
