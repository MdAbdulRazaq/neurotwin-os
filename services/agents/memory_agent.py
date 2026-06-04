"""
Memory Agent — Listens to conversation events and stores key facts in Neo4j as UserMemory nodes.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase

logger = logging.getLogger("agents.memory")

class MemoryAgent:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
        self.redis = None
        self.pubsub = None
        self.driver = None

    async def start(self):
        # Connect to Redis
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("neurotwin:conversations")
        logger.info("MemoryAgent subscribed to neurotwin:conversations")

        # Connect to Neo4j
        self.driver = AsyncGraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
        async with self.driver.session() as session:
            await session.run("CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:UserMemory) REQUIRE m.id IS UNIQUE")
        logger.info("MemoryAgent connected to Neo4j")

        # Listen for messages
        await self._listen()

    async def _listen(self):
        while True:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    await self._process_message(message)
            except asyncio.CancelledError:
                logger.info("MemoryAgent stopped")
                break
            except Exception as e:
                logger.error(f"MemoryAgent error: {e}", exc_info=True)
                await asyncio.sleep(1)  # avoid tight loop

    async def _process_message(self, message):
        try:
            data = json.loads(message["data"])
            user_id = data.get("user_id")
            content = data.get("content", "")
            if not user_id:
                return

            # Extract simple fact (placeholder: store snippet)
            memory_id = f"mem_{int(datetime.utcnow().timestamp() * 1000)}"
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (u:User {id: $user_id})
                    CREATE (m:UserMemory {
                        id: $memory_id,
                        content: $content,
                        timestamp: $timestamp
                    })
                    MERGE (u)-[:HAS_MEMORY]->(m)
                    """,
                    user_id=user_id,
                    memory_id=memory_id,
                    content=content[:200],
                    timestamp=datetime.utcnow().isoformat()
                )
            logger.info(f"Stored memory for user {user_id}: {content[:50]}...")
        except Exception as e:
            logger.error(f"Failed to process memory: {e}", exc_info=True)

    async def stop(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis:
            await self.redis.close()
        if self.driver:
            await self.driver.close()

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    agent = MemoryAgent()
    try:
        await agent.start()
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
