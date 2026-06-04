import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app, ActionEngine
from app.models_plan import ActionPlan, PlanStep

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
@patch("app.main.Planner")
@patch("app.main.PlanExecutor")
async def test_multi_step_plan_execution(mock_executor_cls, mock_planner_cls, client):
    mock_planner = AsyncMock()
    step1 = PlanStep("s1", "open_url", {"url": "https://youtube.com"}, "pending", required=True)
    step2 = PlanStep("s2", "play_music", {"query": "lofi"}, "pending", required=True)
    mock_plan = ActionPlan("p1", "u1", "open youtube and play lofi", "pending", 0, 0, [step1, step2])
    mock_planner.create_plan.return_value = mock_plan
    mock_planner_cls.return_value = mock_planner

    mock_executor = AsyncMock()
    mock_executor.execute_plan.return_value = {
        "plan_id": "p1", "status": "completed", "total_steps": 2,
        "succeeded": 2, "failed": 0,
        "steps": [
            {"step_id": "s1", "action_type": "open_url", "status": "success", "result": "ok", "error": None},
            {"step_id": "s2", "action_type": "play_music", "status": "success", "result": "ok", "error": None}
        ],
        "overall_result": "Plan completed: 2/2 steps succeeded"
    }
    mock_executor_cls.return_value = mock_executor

    with patch("app.main.ActionEngine") as mock_engine_cls:
        mock_engine = AsyncMock()
        mock_engine.planner = mock_planner
        mock_engine.executor = mock_executor
        mock_engine_cls.return_value = mock_engine
        import app.main
        app.main.engine = mock_engine

        resp = await client.post("/v1/action/execute", json={"text": "open youtube and play lofi", "user_id": "u1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Plan completed" in data["result"]
