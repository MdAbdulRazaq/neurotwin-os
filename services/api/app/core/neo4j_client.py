"""
NEUROTWIN OS — Neo4j Graph Client
Extended with Digital Twin behavioral graph schema.
Patterns inspired by code-review-graph + behavior-engine SKILL.md
"""

import logging
import time
from typing import Dict, List, Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger("neurotwin.neo4j")


class Neo4jClient:
    """Async Neo4j client for Digital Twin graph memory."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._uri = uri
        self._user = user

    async def close(self):
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed")

    # ── Core message node ────────────────────────────────────────────────────

    async def create_message_node(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        message_id: str,
        emotion: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """Create Message node linked to User and Session."""
        if timestamp is None:
            timestamp = time.time()
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (s:Session {id: $session_id})
        MERGE (u)-[:HAS_SESSION]->(s)
        CREATE (m:Message {
            id: $message_id,
            role: $role,
            content: $content,
            emotion: $emotion,
            timestamp: $timestamp
        })
        MERGE (u)-[:SENT]->(m)
        MERGE (m)-[:PART_OF_SESSION]->(s)
        """
        try:
            async with self._driver.session() as session:
                await session.run(query, {
                    "user_id": user_id, "session_id": session_id,
                    "message_id": message_id, "role": role,
                    "content": content, "emotion": emotion, "timestamp": timestamp,
                })
            logger.debug(f"Created message node {message_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to create message node: {e}")
            raise

    # ── Digital Twin behavioral graph ────────────────────────────────────────

    async def update_emotion_pattern(
        self, user_id: str, emotion: str, timestamp: Optional[float] = None
    ) -> None:
        """Track emotion frequency pattern for Digital Twin profile."""
        if timestamp is None:
            timestamp = time.time()
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (ep:EmotionPattern {user_id: $user_id, emotion: $emotion})
        ON CREATE SET ep.count = 1, ep.first_seen = $timestamp, ep.last_seen = $timestamp
        ON MATCH SET ep.count = ep.count + 1, ep.last_seen = $timestamp
        MERGE (u)-[:HAS_PATTERN]->(ep)
        """
        try:
            async with self._driver.session() as session:
                await session.run(query, {
                    "user_id": user_id, "emotion": emotion, "timestamp": timestamp
                })
        except Exception as e:
            logger.warning(f"Emotion pattern update skipped: {e}")

    async def create_topic_node(
        self, user_id: str, topic: str, session_id: str
    ) -> None:
        """Track topics discussed for behavioral modeling."""
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (t:Topic {name: $topic})
        ON CREATE SET t.mention_count = 1
        ON MATCH SET t.mention_count = t.mention_count + 1
        MERGE (u)-[:PREFERS]->(t)
        MERGE (s:Session {id: $session_id})
        MERGE (s)-[:DISCUSSED]->(t)
        """
        try:
            async with self._driver.session() as session:
                await session.run(query, {
                    "user_id": user_id, "topic": topic, "session_id": session_id
                })
        except Exception as e:
            logger.warning(f"Topic node skipped: {e}")

    async def link_session_chain(
        self, prev_session_id: str, next_session_id: str
    ) -> None:
        """Create temporal chain between sessions for behavioral continuity."""
        query = """
        MERGE (s1:Session {id: $prev_session_id})
        MERGE (s2:Session {id: $next_session_id})
        MERGE (s1)-[:FOLLOWED_BY]->(s2)
        """
        try:
            async with self._driver.session() as session:
                await session.run(query, {
                    "prev_session_id": prev_session_id,
                    "next_session_id": next_session_id
                })
        except Exception as e:
            logger.warning(f"Session chain link skipped: {e}")

    # ── Twin profile queries ─────────────────────────────────────────────────

    async def get_user_twin_profile(self, user_id: str) -> Dict:
        """Query full behavioral twin profile from graph."""
        try:
            async with self._driver.session() as session:
                # Emotion patterns
                emotion_result = await session.run("""
                    MATCH (u:User {id: $uid})-[:HAS_PATTERN]->(ep:EmotionPattern)
                    RETURN ep.emotion AS emotion, ep.count AS count
                    ORDER BY ep.count DESC LIMIT 5
                """, {"uid": user_id})
                emotions = [{"emotion": r["emotion"], "count": r["count"]}
                           async for r in emotion_result]

                # Topic preferences
                topic_result = await session.run("""
                    MATCH (u:User {id: $uid})-[:PREFERS]->(t:Topic)
                    RETURN t.name AS topic, t.mention_count AS count
                    ORDER BY t.mention_count DESC LIMIT 10
                """, {"uid": user_id})
                topics = [{"topic": r["topic"], "count": r["count"]}
                         async for r in topic_result]

                # Message count
                msg_result = await session.run("""
                    MATCH (u:User {id: $uid})-[:SENT]->(m:Message)
                    RETURN count(m) AS total
                """, {"uid": user_id})
                msg_record = await msg_result.single()
                total_messages = msg_record["total"] if msg_record else 0

            return {
                "user_id": user_id,
                "emotion_patterns": emotions,
                "top_topics": topics,
                "total_messages": total_messages,
                "dominant_emotion": emotions[0]["emotion"] if emotions else "neutral",
            }
        except Exception as e:
            logger.warning(f"Twin profile query failed: {e}")
            return {"user_id": user_id, "error": str(e)}

    async def get_node_count(self) -> int:
        """Get total node count for health verification."""
        try:
            async with self._driver.session() as session:
                result = await session.run("MATCH (n) RETURN count(n) AS total")
                record = await result.single()
                return record["total"] if record else 0
        except Exception as e:
            logger.warning(f"Node count query failed: {e}")
            return 0
