"""
NEUROTWIN Digital Twin — Identity Graph (Phase 4)
Neo4j graph: User → HAS_TRAIT → Trait
             User → HAS_PATTERN → Pattern
             User → HAS_STATE → CognitiveState
             User → HAD_TIMELINE → TimelineEvent
All ops async. trace_id on every call.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase

from .logging_utils import get_trace_id, generate_trace_id, set_trace_id

logger = logging.getLogger(__name__)


class IdentityGraph:
    """Manages the Neo4j identity graph for every user's digital twin."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self._driver.close()

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    async def ensure_user(self, user_id: str) -> None:
        """Idempotently create User node."""
        async with self._driver.session() as s:
            await s.run("MERGE (u:User {id: $uid})", uid=user_id)

    async def ensure_indexes(self) -> None:
        """Create indexes for fast lookups."""
        queries = [
            "CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.id)",
            "CREATE INDEX trait_name IF NOT EXISTS FOR (t:Trait) ON (t.name)",
            "CREATE INDEX pattern_type IF NOT EXISTS FOR (p:Pattern) ON (p.type)",
        ]
        async with self._driver.session() as s:
            for q in queries:
                try:
                    await s.run(q)
                except Exception as e:
                    logger.warning("Index create skipped", extra={"error": str(e)})

    # ── Traits ────────────────────────────────────────────────────────────────

    async def upsert_trait(self, user_id: str, trait_name: str,
                           value: float, source: str = "synthesized") -> None:
        """Create or update HAS_TRAIT relationship."""
        now = datetime.now(timezone.utc).isoformat()
        async with self._driver.session() as s:
            await s.run("""
                MERGE (u:User {id: $uid})
                MERGE (t:Trait {name: $name})
                MERGE (u)-[r:HAS_TRAIT]->(t)
                SET r.value = $value,
                    r.source = $source,
                    r.updated_at = $now
            """, uid=user_id, name=trait_name, value=value, source=source, now=now)
        logger.debug("Trait upserted", extra={"user_id": user_id, "trait": trait_name, "value": value})

    async def get_traits(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all traits for a user."""
        async with self._driver.session() as s:
            result = await s.run("""
                MATCH (u:User {id: $uid})-[r:HAS_TRAIT]->(t:Trait)
                RETURN t.name AS name, r.value AS value,
                       r.source AS source, r.updated_at AS updated_at
                ORDER BY r.value DESC
            """, uid=user_id)
            return [dict(rec) async for rec in result]


    # ── Patterns ──────────────────────────────────────────────────────────────

    async def upsert_pattern(self, user_id: str, pattern_type: str,
                             confidence: float, evidence_count: int,
                             metadata: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with self._driver.session() as s:
            await s.run("""
                MERGE (u:User {id: $uid})
                MERGE (p:Pattern {type: $ptype, user_id: $uid})
                MERGE (u)-[r:HAS_PATTERN]->(p)
                SET p.confidence     = $conf,
                    p.evidence_count = $ev,
                    p.last_updated   = $now,
                    r.updated_at     = $now
            """, uid=user_id, ptype=pattern_type, conf=confidence,
                 ev=evidence_count, now=now)

    async def get_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        async with self._driver.session() as s:
            result = await s.run("""
                MATCH (u:User {id: $uid})-[:HAS_PATTERN]->(p:Pattern)
                RETURN p.type AS type, p.confidence AS confidence,
                       p.evidence_count AS evidence_count,
                       p.last_updated AS last_updated
                ORDER BY p.confidence DESC
            """, uid=user_id)
            return [dict(rec) async for rec in result]

    # ── Cognitive State ───────────────────────────────────────────────────────

    async def upsert_state(self, user_id: str, state: Dict[str, float]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with self._driver.session() as s:
            await s.run("""
                MERGE (u:User {id: $uid})
                MERGE (cs:CognitiveState {user_id: $uid})
                MERGE (u)-[r:HAS_STATE]->(cs)
                SET cs.focus_level       = $focus,
                    cs.fatigue           = $fatigue,
                    cs.motivation        = $motivation,
                    cs.consistency_score = $consistency,
                    cs.updated_at        = $now,
                    r.updated_at         = $now
            """, uid=user_id,
                 focus=state.get("focus_level", 0.5),
                 fatigue=state.get("fatigue", 0.2),
                 motivation=state.get("motivation", 0.6),
                 consistency=state.get("consistency_score", 0.5),
                 now=now)

    async def get_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self._driver.session() as s:
            result = await s.run("""
                MATCH (u:User {id: $uid})-[:HAS_STATE]->(cs:CognitiveState)
                RETURN cs.focus_level AS focus_level,
                       cs.fatigue AS fatigue,
                       cs.motivation AS motivation,
                       cs.consistency_score AS consistency_score,
                       cs.updated_at AS updated_at
            """, uid=user_id)
            rec = await result.single()
            return dict(rec) if rec else None

    # ── Timeline ──────────────────────────────────────────────────────────────

    async def add_timeline_event(self, user_id: str, event_type: str,
                                 data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        import json as _json
        async with self._driver.session() as s:
            await s.run("""
                MATCH (u:User {id: $uid})
                CREATE (e:TimelineEvent {
                    user_id:    $uid,
                    event_type: $etype,
                    data_json:  $data,
                    occurred_at: $now
                })
                CREATE (u)-[:HAD_TIMELINE]->(e)
            """, uid=user_id, etype=event_type,
                 data=_json.dumps(data), now=now)

    async def get_timeline(self, user_id: str,
                           limit: int = 50) -> List[Dict[str, Any]]:
        import json as _json
        async with self._driver.session() as s:
            result = await s.run("""
                MATCH (u:User {id: $uid})-[:HAD_TIMELINE]->(e:TimelineEvent)
                RETURN e.event_type AS event_type,
                       e.data_json  AS data_json,
                       e.occurred_at AS occurred_at
                ORDER BY e.occurred_at DESC
                LIMIT $lim
            """, uid=user_id, lim=limit)
            events = []
            async for rec in result:
                try:
                    events.append({
                        "event_type":  rec["event_type"],
                        "data":        _json.loads(rec["data_json"] or "{}"),
                        "occurred_at": rec["occurred_at"],
                    })
                except Exception:
                    continue
            return events
