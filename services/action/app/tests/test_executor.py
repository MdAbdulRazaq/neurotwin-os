import asyncio
import pytest
from unittest.mock import AsyncMock
from app.main import ActionEngine, ActionType, ActionResult
from app.models_plan import PlanStep, ActionPlan
from app.plan_executor import PlanExecutor


class MockEngineForExecutor:
    def __init__(self):
        self.redis = AsyncMock()
        self.executors = {ActionType.TELL_JOKE: MockJokeExecutor()}
        self.pending_confirmations = {}
        self._safety_check = lambda *args: True
        self.request_confirmation = AsyncMock(return_value=True)


class MockJokeExecutor:
    call_count = 0
    should_fail = False

    async def execute(self, params, user_id):
        MockJokeExecutor.call_count += 1
        if MockJokeExecutor.should_fail:
            raise Exception("Executor failed")
        return ActionResult(success=True, action="tell_joke", result="Mock joke")


@pytest.fixture
def executor_fixture():
    engine = MockEngineForExecutor()
    return PlanExecutor(engine)


@pytest.mark.asyncio
async def test_retry_success_on_third_try(executor_fixture):
    attempt = 0

    async def flaky_execute(params, user_id):
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise Exception("fail")
        return ActionResult(success=True, action="tell_joke", result="finally")

    executor_fixture.engine.executors[ActionType.TELL_JOKE].execute = flaky_execute

    step = PlanStep(
        step_id="s1", action_type="tell_joke", params={},
        status="pending", required=True, max_retries=3, retry_count=0
    )
    plan = ActionPlan(
        plan_id="p1", user_id="u1", goal="tell joke",
        status="pending", created_at=0, updated_at=0,
        steps=[step], current_step_index=0
    )
    await executor_fixture._execute_step(step, "u1", plan)
    assert step.status == "success"
    assert step.retry_count == 2


@pytest.mark.asyncio
async def test_required_step_failure_on_safety_block(executor_fixture):
    """Safety check failure marks step as failed — executor_plan handles abort logic."""
    step1 = PlanStep(step_id="s1", action_type="tell_joke", params={}, status="pending", required=True)
    step2 = PlanStep(step_id="s2", action_type="tell_joke", params={}, status="pending", required=True)
    plan = ActionPlan(
        plan_id="p1", user_id="u1", goal="two jokes",
        status="pending", created_at=0, updated_at=0,
        steps=[step1, step2], current_step_index=0
    )
    executor_fixture.engine._safety_check = lambda *args: False
    await executor_fixture._execute_step(step1, "u1", plan)
    assert step1.status == "failed"
    assert "safety" in (step1.error or "").lower()


@pytest.mark.asyncio
async def test_execute_plan_aborts_on_required_failure(executor_fixture):
    """execute_plan skips remaining steps when a required step fails."""
    step1 = PlanStep(step_id="s1", action_type="tell_joke", params={}, status="pending", required=True)
    step2 = PlanStep(step_id="s2", action_type="tell_joke", params={}, status="pending", required=True)
    plan = ActionPlan(
        plan_id="p1", user_id="u1", goal="two jokes",
        status="pending", created_at=0, updated_at=0,
        steps=[step1, step2], current_step_index=0
    )
    executor_fixture.engine._safety_check = lambda *args: False  # fails step1
    summary = await executor_fixture.execute_plan(plan)
    assert step1.status == "failed"
    assert step2.status == "skipped"
    assert plan.status == "failed"


@pytest.mark.asyncio
async def test_confirmation_timeout_fails(executor_fixture):
    step = PlanStep(step_id="s1", action_type="tell_joke", params={}, status="pending", required=True)
    plan = ActionPlan(
        plan_id="p1", user_id="u1", goal="joke",
        status="pending", created_at=0, updated_at=0,
        steps=[step], current_step_index=0
    )
    executor_fixture.engine.request_confirmation = AsyncMock(side_effect=asyncio.TimeoutError())
    executor_fixture.engine._safety_check = lambda *args: True
    await executor_fixture._execute_step(step, "u1", plan)
    assert step.status == "failed"
