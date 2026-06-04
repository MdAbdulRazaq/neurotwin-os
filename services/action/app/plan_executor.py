import asyncio
import json
import logging
import time
from typing import Dict, Any

from .main import ActionEngine, ActionType
from .models_plan import ActionPlan, PlanStep


class PlanExecutor:
    def __init__(self, engine: "ActionEngine"):
        self.engine = engine
        self.logger = logging.getLogger("action.executor")

    async def execute_plan(self, plan: ActionPlan) -> Dict[str, Any]:
        """Execute all steps in the plan sequentially."""
        plan.status = "running"
        await self._persist_plan(plan)

        for idx, step in enumerate(plan.steps):
            plan.current_step_index = idx
            await self._persist_plan(plan)
            await self._execute_step(step, plan.user_id, plan)

            if step.status == "failed" and step.required:
                # Abort: mark remaining steps as skipped
                for remaining in plan.steps[idx + 1:]:
                    remaining.status = "skipped"
                    remaining.error = "Aborted due to previous step failure"
                plan.status = "failed"
                await self._persist_plan(plan)
                await self._publish_completion(plan)
                return self._summarize_plan(plan)

        plan.status = "completed"
        await self._persist_plan(plan)
        await self._publish_completion(plan)
        return self._summarize_plan(plan)

    async def _execute_step(self, step: PlanStep, user_id: str, plan: ActionPlan):
        """Execute a single step with retry, safety check, and confirmation."""
        self.logger.info(f"Executing step {step.step_id}: {step.action_type}")
        step.status = "running"
        await self._persist_plan(plan)

        # Resolve action type — fail fast on unknown
        try:
            action_type_enum = ActionType(step.action_type)
        except ValueError:
            step.status = "failed"
            step.error = f"Unknown action type: {step.action_type}"
            await self._persist_plan(plan)
            await self._publish_update(step, plan.plan_id)
            return

        # Safety check — not retried
        if not self.engine._safety_check(action_type_enum, step.params):
            step.status = "failed"
            step.error = "Blocked by safety check"
            await self._persist_plan(plan)
            await self._publish_update(step, plan.plan_id)
            return

        # Confirmation — not retried
        try:
            confirmed = await self.engine.request_confirmation(
                action_type_enum, step.params, user_id, session_id=""
            )
        except Exception:
            confirmed = False

        if not confirmed:
            step.status = "failed"
            step.error = "Confirmation denied or timed out"
            await self._persist_plan(plan)
            await self._publish_update(step, plan.plan_id)
            return

        # Retry loop wraps only the actual execution
        while step.retry_count <= step.max_retries:
            try:
                executor = self.engine.executors[action_type_enum]
                result = await executor.execute(step.params, user_id)
                step.status = "success"
                step.result = result.result
                step.details = result.details
                await self._persist_plan(plan)
                await self._publish_update(step, plan.plan_id)
                return
            except Exception as e:
                step.retry_count += 1
                self.logger.warning(
                    f"Step {step.step_id} failed, retry {step.retry_count}/{step.max_retries}: {e}"
                )
                if step.retry_count > step.max_retries:
                    step.status = "failed"
                    step.error = f"Max retries exceeded: {str(e)}"
                    await self._persist_plan(plan)
                    await self._publish_update(step, plan.plan_id)
                    return
                backoff = 2 ** (step.retry_count - 1)  # 1, 2, 4 seconds
                await asyncio.sleep(backoff)

    # ── Persistence ────────────────────────────────────────────────────────────

    async def _persist_plan(self, plan: ActionPlan):
        """Store entire plan state in Redis."""
        key = f"action:plan:{plan.plan_id}"
        data = {
            "plan_id": plan.plan_id,
            "user_id": plan.user_id,
            "goal": plan.goal,
            "status": plan.status,
            "created_at": str(plan.created_at),
            "updated_at": str(time.time()),
            "current_step_index": str(plan.current_step_index),
            "steps_json": json.dumps([
                {
                    "step_id": s.step_id,
                    "action_type": s.action_type,
                    "params": s.params,
                    "status": s.status,
                    "retry_count": s.retry_count,
                    "required": s.required,
                    "result": s.result,
                    "error": s.error,
                    "details": s.details,
                }
                for s in plan.steps
            ]),
        }
        await self.engine.redis.hset(key, mapping=data)
        await self.engine.redis.zadd(
            f"action:user:{plan.user_id}:plans", {plan.plan_id: plan.created_at}
        )

    # ── Pub/Sub ────────────────────────────────────────────────────────────────

    async def _publish_update(self, step: PlanStep, plan_id: str):
        payload = {
            "plan_id": plan_id,
            "step_id": step.step_id,
            "action_type": step.action_type,
            "status": step.status,
            "result": step.result,
            "error": step.error,
            "timestamp": time.time(),
        }
        try:
            await self.engine.redis.publish(
                "neurotwin:plan_execution_updates", json.dumps(payload)
            )
        except Exception as e:
            self.logger.error(f"Failed to publish plan update: {e}")

    async def _publish_completion(self, plan: ActionPlan):
        summary = self._summarize_plan(plan)
        try:
            await self.engine.redis.publish(
                "neurotwin:plan_completed", json.dumps(summary)
            )
        except Exception as e:
            self.logger.error(f"Failed to publish plan completion: {e}")

    # ── Summarize ─────────────────────────────────────────────────────────────

    def _summarize_plan(self, plan: ActionPlan) -> Dict[str, Any]:
        succeeded = sum(1 for s in plan.steps if s.status == "success")
        failed = sum(1 for s in plan.steps if s.status == "failed")
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "total_steps": len(plan.steps),
            "succeeded": succeeded,
            "failed": failed,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action_type": s.action_type,
                    "status": s.status,
                    "result": s.result,
                    "error": s.error,
                }
                for s in plan.steps
            ],
            "overall_result": f"Plan {plan.status}: {succeeded}/{len(plan.steps)} steps succeeded",
        }
