"""
Unit tests for PersonaAgent (T6 — Dynamic Personality Evolution)
services/agents/tests/test_persona.py
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from persona_agent import PersonaAgent


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def agent():
    a = PersonaAgent()
    a.pool = AsyncMock()
    a.neo4j_driver = AsyncMock()
    a.redis = AsyncMock()
    return a


def _make_neo4j_session(agent):
    """Wire neo4j_driver.session() to return a proper async context manager."""
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    agent.neo4j_driver.session = MagicMock(return_value=cm)
    return session


def _make_pg_conn(agent, rows):
    """Wire pool.acquire() to return a proper async context manager."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    agent.pool.acquire = MagicMock(return_value=cm)
    return conn


def _pg_row(user_id: str, content: str):
    return {"user_id": user_id, "content": content}


# ── _infer_and_write ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_infer_positive_trait(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u1", ["great day today", "awesome work done", "love this"])
    for c in session.run.call_args_list:
        if c.args and "HAS_TRAIT" in c.args[0]:
            assert c.kwargs.get("trait") == "positive"
            break


@pytest.mark.asyncio
async def test_infer_stressed_trait(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u2", ["so tired and stressed", "hate this terrible day", "awful mood"])
    for c in session.run.call_args_list:
        if c.args and "HAS_TRAIT" in c.args[0]:
            assert c.kwargs.get("trait") == "stressed"
            break


@pytest.mark.asyncio
async def test_infer_neutral_trait(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u3", ["great and happy", "sad and bad today"])
    for c in session.run.call_args_list:
        if c.args and "HAS_TRAIT" in c.args[0]:
            assert c.kwargs.get("trait") == "neutral"
            break


@pytest.mark.asyncio
async def test_infer_action_preference_learning(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u4", ["i need to study more", "going to the gym today", "must study hard"])
    prefers_calls = [c for c in session.run.call_args_list if c.args and "PREFERS" in c.args[0]]
    actions_written = {c.kwargs.get("action") for c in prefers_calls}
    assert "learning" in actions_written
    assert "health" in actions_written


@pytest.mark.asyncio
async def test_infer_no_action_on_neutral_message(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u5", ["hello there", "how are you", "what time is it"])
    prefers_calls = [c for c in session.run.call_args_list if c.args and "PREFERS" in c.args[0]]
    assert len(prefers_calls) == 0


@pytest.mark.asyncio
async def test_neo4j_user_merge_called(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u6", ["hello"])
    merge_calls = [c for c in session.run.call_args_list if c.args and "MERGE (u:User" in c.args[0]]
    assert len(merge_calls) == 1
    assert merge_calls[0].kwargs.get("uid") == "u6"


@pytest.mark.asyncio
async def test_redis_profile_cached(agent):
    session = AsyncMock()
    await agent._infer_and_write(session, "u7", ["great work today"])
    agent.redis.setex.assert_called_once()
    call_args = agent.redis.setex.call_args
    key = call_args.args[0] if call_args.args else call_args.kwargs.get("name", "")
    assert "persona:u7:profile" in key
    ttl = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("time")
    assert ttl == 3600
    raw = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("value")
    data = json.loads(raw)
    assert data["user_id"] == "u7"
    assert "trait" in data
    assert "preferences" in data


@pytest.mark.asyncio
async def test_redis_not_called_when_none(agent):
    agent.redis = None
    session = AsyncMock()
    await agent._infer_and_write(session, "u8", ["good day"])  # must not raise


# ── _update_profiles ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_profiles_no_messages(agent):
    _make_pg_conn(agent, [])
    session = _make_neo4j_session(agent)
    await agent._update_profiles()
    session.run.assert_not_called()


@pytest.mark.asyncio
async def test_update_profiles_single_user(agent):
    rows = [_pg_row("user-1", "great awesome day"), _pg_row("user-1", "love this excellent work")]
    _make_pg_conn(agent, rows)
    session = _make_neo4j_session(agent)
    await agent._update_profiles()
    trait_calls = [c for c in session.run.call_args_list if c.args and "HAS_TRAIT" in c.args[0]]
    assert len(trait_calls) == 1
    assert trait_calls[0].kwargs.get("uid") == "user-1"
    assert trait_calls[0].kwargs.get("trait") == "positive"


@pytest.mark.asyncio
async def test_update_profiles_multiple_users(agent):
    rows = [_pg_row("alice", "happy great wonderful"), _pg_row("bob", "terrible awful stressed")]
    _make_pg_conn(agent, rows)
    session = _make_neo4j_session(agent)
    await agent._update_profiles()
    trait_calls = [c for c in session.run.call_args_list if c.args and "HAS_TRAIT" in c.args[0]]
    assert len(trait_calls) == 2
    uids = {c.kwargs.get("uid") for c in trait_calls}
    traits = {c.kwargs.get("trait") for c in trait_calls}
    assert uids == {"alice", "bob"}
    assert "positive" in traits
    assert "stressed" in traits


@pytest.mark.asyncio
async def test_update_profiles_aggregates_messages_per_user(agent):
    rows = [_pg_row("u9", "great day"), _pg_row("u9", "good progress"), _pg_row("u9", "love this work")]
    _make_pg_conn(agent, rows)
    session = _make_neo4j_session(agent)
    await agent._update_profiles()
    merge_calls = [c for c in session.run.call_args_list if c.args and "MERGE (u:User" in c.args[0]]
    assert len(merge_calls) == 1


@pytest.mark.asyncio
async def test_update_profiles_missing_pool(agent):
    agent.pool = None
    await agent._update_profiles()   # must not raise


@pytest.mark.asyncio
async def test_update_profiles_missing_neo4j(agent):
    agent.neo4j_driver = None
    await agent._update_profiles()   # must not raise


# ── Action count aggregation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_count_aggregated_correctly(agent):
    """'study' mentioned 3x → PREFERS learning with count=3."""
    session = AsyncMock()
    await agent._infer_and_write(session, "u10", ["i study hard", "must study more", "time to study"])
    prefers_calls = [
        c for c in session.run.call_args_list
        if c.args and "PREFERS" in c.args[0] and c.kwargs.get("action") == "learning"
    ]
    assert len(prefers_calls) == 1
    assert prefers_calls[0].kwargs.get("count") == 3


@pytest.mark.asyncio
async def test_multiple_action_categories(agent):
    """'music' and 'work' → entertainment + productivity both written."""
    session = AsyncMock()
    await agent._infer_and_write(session, "u11", ["listening to music all day", "work meeting done", "music helps me work"])
    prefers_calls = [c for c in session.run.call_args_list if c.args and "PREFERS" in c.args[0]]
    actions = {c.kwargs.get("action") for c in prefers_calls}
    assert "entertainment" in actions
    assert "productivity" in actions
