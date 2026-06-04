"""
Emotion Agent — Listens to emotion events, tracks patterns in Neo4j, and triggers visual updates.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import httpx
import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase

logger = logging.getLogger("agents.emotion")

class EmotionAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
        self.visual_identity_url = os.getenv("VISUAL_IDENTITY_URL", "http://visual-identity:8005")
        self.redis = None
        self.pubsub = None
        self.driver = None

    async def start(self):
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("neurotwin:emotion")
        logger.info("EmotionAgent subscribed to neurotwin:emotions")

        self.driver = AsyncGraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
        async with self.driver.session() as session:
            await session.run("CREATE CONSTRAINT emotion_pattern_id IF NOT EXISTS FOR (ep:EmotionPattern) REQUIRE ep.id IS UNIQUE")
        logger.info("EmotionAgent connected to Neo4j")

        await self._listen()

    async def _listen(self):
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    await self._process_emotion(message)
            except asyncio.CancelledError:
                logger.info("EmotionAgent stopped")
                break
            except Exception as e:
                logger.error(f"EmotionAgent error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_emotion(self, message):
        try:
            data = json.loads(message["data"])
            user_id = data.get("user_id")
            emotion = data.get("emotion")
            intensity = data.get("intensity", 0.5)
            if not user_id or not emotion:
                return

            # Store in Neo4j as EmotionPattern
            pattern_id = f"ep_{int(datetime.utcnow().timestamp() * 1000)}"
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (u:User {id: $user_id})
                    CREATE (ep:EmotionPattern {
                        id: $pattern_id,
                        emotion: $emotion,
                        intensity: $intensity,
                        timestamp: $timestamp
                    })
                    MERGE (u)-[:HAS_EMOTION_PATTERN]->(ep)
                    """,
                    user_id=user_id,
                    pattern_id=pattern_id,
                    emotion=emotion,
                    intensity=intensity,
                    timestamp=datetime.utcnow().isoformat()
                )
            logger.debug(f"Stored emotion pattern for {user_id}: {emotion}")

            # Trigger visual identity update automatically by calling the service
            # Fire-and-forget; do not block on response
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    await client.post(
                        f"{self.visual_identity_url}/v1/style/emotion",
                        json={"emotion": emotion, "intensity": intensity}
                    )
            except Exception as e:
                logger.warning(f"Failed to notify Visual Identity: {e}")

        except Exception as e:
            logger.error(f"Failed to process emotion: {e}", exc_info=True)

    async def stop(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis:
            await self.redis.close()
        if self.driver:
            await self.driver.close()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    agent = EmotionAgent()
    try:
        await agent.start()
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
