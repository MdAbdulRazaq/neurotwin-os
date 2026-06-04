"""
Agents HTTP API — FastAPI wrapper exposing agent methods to the orchestrator.
Runs background agents as asyncio tasks.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Ensure the agents service directory is on the path for bare imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel
from user_profile import UserProfileBuilder
import os
import redis.asyncio as aioredis

logger = logging.getLogger("agents.api")

app = FastAPI()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
REDIS_URL = os.getenv("REDIS_URL", "redis://neurotwin-redis:6379/0")
driver = None


@app.on_event("startup")
async def startup():
    global driver
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Start background agents
    from memory_agent import main as memory_main
    from emotion_agent import main as emotion_main
    from persona_agent import main as persona_main
    from insight_agent import main as insight_main
    asyncio.create_task(memory_main())
    asyncio.create_task(emotion_main())
    asyncio.create_task(persona_main())
    asyncio.create_task(insight_main())
    logger.info("Agents started")


@app.on_event("shutdown")
async def shutdown():
    global driver
    if driver:
        await driver.close()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/get_twin_profile")
async def get_twin_profile(user_id: str):
    """Return twin profile (traits and preferences) from Neo4j."""
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j not connected")
    async with driver.session() as session:
        # Trait: HAS_TRAIT
        traits_result = await session.run(
            "MATCH (u:User {id: $user_id})-[r:HAS_TRAIT]->(t:Trait) RETURN t.name as name, r.value as value, r.timestamp as ts",
            user_id=user_id
        )
        traits = []
        async for rec in traits_result:
            traits.append({
                "name": rec["name"],
                "value": rec["value"],
                "last_updated": rec["ts"]
            })
        # Preferences: PREFERS
        actions_result = await session.run(
            "MATCH (u:User {id: $user_id})-[r:PREFERS]->(a:Action) RETURN a.name as type, r.timestamp as ts",
            user_id=user_id
        )
        preferences = []
        async for rec in actions_result:
            preferences.append({
                "action": rec["type"],
                "last_used": rec["ts"]
            })

        return {
            "user_id": user_id,
            "twin_profile": {
                "personality_traits": [t["name"] for t in traits],
                "trait_values": {t["name"]: t["value"] for t in traits},
                "preferred_actions": [p["action"] for p in preferences],
            },
            "last_updated": datetime.utcnow().isoformat()
        }


@app.get("/graph")
async def get_graph(user_id: str):
    """Return full graph connected to the user for brain visualization."""
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j not connected")
    async with driver.session() as session:
        result = await session.run(
            "MATCH (u:User {id: $uid})-[r]-(n) RETURN u, r, n",
            uid=user_id
        )
        nodes = {}
        links = []
        async for record in result:
            u_node = record["u"]
            n_node = record["n"]
            rel = record["r"]
            # Add nodes (user and connected nodes)
            for node in [u_node, n_node]:
                node_id = node.get("id")
                if node_id is None:
                    node_id = str(node.id)
                nodes[node_id] = {
                    "id": node_id,
                    "labels": list(node.labels),
                    "properties": dict(node)
                }
            # Add link
            start_id = rel.start_node.get("id") if rel.start_node.get("id") else str(rel.start_node.id)
            end_id = rel.end_node.get("id") if rel.end_node.get("id") else str(rel.end_node.id)
            links.append({
                "source": start_id,
                "target": end_id,
                "type": rel.type
            })
        return {"nodes": list(nodes.values()), "links": links}


@app.get("/analytics/emotions")
async def get_emotion_analytics(user_id: str, days: int = 7):
    """Return emotion history from Neo4j EmotionPattern nodes."""
    if not driver:
        raise HTTPException(status_code=500, detail="Neo4j not connected")
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (u:User {id: $uid})-[:HAS_EMOTION]->(e:EmotionPattern)
            WHERE e.timestamp > datetime() - duration({days: $days})
            RETURN e.timestamp as ts, e.emotion as emotion, e.intensity as intensity
            ORDER BY e.ts
            """,
            uid=user_id, days=days
        )
        emotions = []
        async for rec in result:
            ts = rec["ts"]
            iso = ts.iso_format() if hasattr(ts, "iso_format") else str(ts)
            emotions.append({
                "timestamp": iso,
                "emotion": rec["emotion"],
                "intensity": rec["intensity"]
            })
        return {"emotions": emotions}
