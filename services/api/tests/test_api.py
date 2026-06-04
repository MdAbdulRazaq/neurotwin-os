"""
NEUROTWIN OS — Backend Test Suite
Tests for auth, conversation, memory, and avatar services.
"""

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.config import settings


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register + login, return auth headers."""
    await client.post("/v1/auth/register", json={
        "email": "test@neurotwin.ai",
        "password": "testpassword123",
        "name": "Test User",
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "test@neurotwin.ai",
        "password": "testpassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "neurotwin-api"


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/v1/auth/register", json={
        "email": "newuser@neurotwin.ai",
        "password": "securepassword99",
        "name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dupe@neurotwin.ai", "password": "pass12345", "name": "Dupe"}
    await client.post("/v1/auth/register", json=payload)
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/v1/auth/register", json={
        "email": "logintest@neurotwin.ai",
        "password": "mypassword123",
        "name": "Login Test",
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "logintest@neurotwin.ai",
        "password": "mypassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/v1/auth/register", json={
        "email": "wrongpw@neurotwin.ai",
        "password": "correct123",
        "name": "Wrong PW",
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "wrongpw@neurotwin.ai",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    resp = await client.get("/v1/user/me")
    assert resp.status_code == 401


# ── Conversation ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session(client, auth_headers):
    resp = await client.post("/v1/conversation/session", json={}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 8


@pytest.mark.asyncio
@patch("app.routers.convo.get_llm_client")
async def test_send_message(mock_llm_factory, client, auth_headers):
    # Mock LLM response
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = MagicMock(
        text="Hello! I'm so glad you reached out. How can I help you today?",
        model="claude-3-5-sonnet",
        total_tokens=50,
        latency_ms=120,
    )
    mock_llm_factory.return_value = mock_llm

    # Create session first
    sess_resp = await client.post("/v1/conversation/session", json={}, headers=auth_headers)
    session_id = sess_resp.json()["session_id"]

    # Send message
    resp = await client.post(
        f"/v1/conversation/{session_id}/message",
        json={"content": "Hello!", "session_id": session_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0
    assert data["session_id"] == session_id


@pytest.mark.asyncio
async def test_conversation_history(client, auth_headers):
    sess_resp = await client.post("/v1/conversation/session", json={}, headers=auth_headers)
    session_id = sess_resp.json()["session_id"]

    resp = await client.get(
        f"/v1/conversation/{session_id}/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)


# ── Memory ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_list(client, auth_headers):
    resp = await client.get("/v1/memory", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "memories" in data
    assert "total" in data


# ── LLM Client Unit Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_client_system_prompt_with_rag():
    from app.core.llm_client import LLMClient
    client = LLMClient.__new__(LLMClient)
    client.provider = "anthropic"
    client.model = "claude-3-5-sonnet"

    system = "You are NEUROTWIN."
    contexts = ["User likes hiking", "User's birthday is March 5"]
    result = client._build_system(system, contexts)

    assert "You are NEUROTWIN." in result
    assert "User likes hiking" in result
    assert "User's birthday is March 5" in result
    assert "Memory 1" in result


@pytest.mark.asyncio
async def test_llm_client_no_rag():
    from app.core.llm_client import LLMClient
    client = LLMClient.__new__(LLMClient)
    result = client._build_system("Base system prompt", None)
    assert result == "Base system prompt"


# ── Avatar ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_avatar_state(client, auth_headers):
    resp = await client.get("/v1/avatar/test-avatar-001/state", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "avatar_id" in data
    assert "current_expression" in data
    assert "is_speaking" in data


@pytest.mark.asyncio
async def test_avatar_set_expression(client, auth_headers):
    resp = await client.post(
        "/v1/avatar/test-avatar-001/expression",
        json={"expression": "smile", "intensity": 0.8, "duration_ms": 2000, "blend": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expression"] == "smile"


# ── Memory Manager Unit Tests ─────────────────────────────────────────────────

def test_memory_importance_scoring():
    from app.core.memory import MemoryManager
    mgr = MemoryManager.__new__(MemoryManager)

    score_high = mgr._score_importance("My birthday is tomorrow, remember this!", "joy")
    score_low = mgr._score_importance("okay", None)

    assert score_high > score_low
    assert 0 <= score_high <= 1
    assert 0 <= score_low <= 1


def test_memory_summarization():
    from app.core.memory import MemoryManager
    mgr = MemoryManager.__new__(MemoryManager)

    short = "Hello world"
    summary = mgr._summarize(short)
    assert summary == short

    long_text = " ".join(["word"] * 50)
    summary_long = mgr._summarize(long_text)
    assert summary_long.endswith("…")
    assert len(summary_long.split()) <= 32
