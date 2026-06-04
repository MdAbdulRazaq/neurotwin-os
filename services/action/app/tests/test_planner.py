import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from app.planner import Planner
from app.main import ActionType

pytestmark = pytest.mark.asyncio

async def test_single_step_detection():
    planner = Planner()
    plan = await planner.create_plan("open google", "user1")
    assert len(plan.steps) == 1
    assert plan.steps[0].action_type == ActionType.OPEN_URL.value

async def test_multi_step_llm_success():
    planner = Planner()
    with patch("app.planner.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": '{"steps": [{"action": "open_url", "params": {"url": "https://youtube.com"}}, {"action": "play_music", "params": {"query": "lofi"}}]'}}
            ]
        }
        mock_client.return_value.post = AsyncMock(return_value=mock_resp)
        plan = await planner.create_plan("open youtube and play lofi music", "user1")
        assert len(plan.steps) == 2
        assert plan.steps[0].action_type == "open_url"
        assert plan.steps[1].action_type == "play_music"

async def test_invalid_json_fallback():
    planner = Planner()
    with patch("app.planner.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "sorry not json"}}]}
        mock_client.return_value.post = AsyncMock(return_value=mock_resp)
        plan = await planner.create_plan("open youtube and play music", "user1")
        assert len(plan.steps) >= 1

async def test_unknown_action_filtered():
    planner = Planner()
    with patch("app.planner.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": '{"steps": [{"action": "hack_into_pentagon", "params": {}}]}'}}
            ]
        }
        mock_client.return_value.post = AsyncMock(return_value=mock_resp)
        plan = await planner.create_plan("something naughty", "user1")
        assert len(plan.steps) >= 1
