"""
Insight Agent — Weekly analysis of user behavior, generates insights stored in PostgreSQL.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

logger = logging.getLogger("agents.insights")

class InsightAgent:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
        self.db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://neurotwin:password@postgres:5432/neurotwin_db")
        self.driver = None
        self.pool = None

    async def start(self):
        self.driver = AsyncGraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
        logger.info("InsightAgent connected to Neo4j")
        if not HAS_ASYNCPG:
            logger.error("asyncpg not installed, InsightAgent disabled")
            return
        self.pool = await asyncpg.create_pool(dsn=self.db_url.replace("+asyncpg", ""))
        logger.info("InsightAgent connected to PostgreSQL")
        await self._weekly_loop()

    async def _weekly_loop(self):
        while True:
            now = datetime.utcnow()
            # Run every 7 days; for demo, could also check every hour and only execute weekly
            await self._generate_insights()
            # Sleep until next week
            await asyncio.sleep(7 * 24 * 3600)

    async def _generate_insights(self):
        logger.info("InsightAgent: generating weekly insights")
        # Example: get top emotions per user from Neo4j
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (u:User)-[:HAS_EMOTION_PATTERN]->(ep:EmotionPattern)
                RETURN u.id as user_id, ep.emotion as emotion, count(*) as count
                ORDER BY u.id, count DESC
                """
            )
            insights = {}
            async for record in result:
                uid = record["user_id"]
                emotion = record["emotion"]
                count = record["count"]
                insights.setdefault(uid, []).append({"emotion": emotion, "count": count})

            # Store insights in PostgreSQL
            async with self.pool.acquire() as conn:
                for uid, emotions in insights.items():
                    summary = ", ".join(f"{e['emotion']}:{e['count']}" for e in emotions[:3])
                    await conn.execute(
                        """
                        INSERT INTO user_insights (user_id, summary, generated_at)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, generated_date) DO UPDATE
                        SET summary = EXCLUDED.summary
                        """,
                        uid, summary, datetime.utcnow()
                    )
            logger.info(f"InsightAgent: stored insights for {len(insights)} users")

    async def stop(self):
        if self.driver:
            await self.driver.close()
        if self.pool:
            await self.pool.close()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    agent = InsightAgent()
    try:
        await agent.start()
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
