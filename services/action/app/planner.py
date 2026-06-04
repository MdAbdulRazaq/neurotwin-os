import httpx
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Tuple

from .main import ActionParser, ActionType
from .models_plan import PlanStep, ActionPlan

class Planner:
    def __init__(self):
        self.nim_url = os.getenv("NIM_PROXY_URL", "http://host.docker.internal:8082/v1")
        self.logger = logging.getLogger("action.planner")
        self.supported_actions = [a.value for a in ActionType if a != ActionType.UNKNOWN]
        self.required_params = {
            "open_url": ["url"],
            "play_music": ["query"],
            "send_whatsapp": ["contact", "message"],
            "check_weather": ["location"],
            "search_web": ["query"],
            "create_event": ["title", "time"],
            "tell_joke": []
        }

    async def create_plan(self, goal: str, user_id: str) -> ActionPlan:
        # Step 1: Check if single step (skip LLM)
        if self._is_single_step(goal):
            action_type, params = ActionParser().parse(goal)
            if action_type != ActionType.UNKNOWN:
                validated = [(action_type.value, params)]
            else:
                validated = []
        else:
            # Step 2: Try LLM
            try:
                validated = await self._llm_plan(goal)
            except Exception as e:
                self.logger.warning(f"LLM planning failed: {e}")
                validated = []

            # Step 3: Fallback rule-based if needed
            if not validated:
                validated = self._rule_split(goal)

        # Step 4: Build plan
        plan_id = str(uuid.uuid4())
        now = time.time()
        steps = [
            PlanStep(
                step_id=str(uuid.uuid4()),
                action_type=at,
                params=p,
                status="pending",
                required=True,
                max_retries=3,
                retry_count=0
            )
            for at, p in validated
        ]
        if not steps:
            steps = [PlanStep(
                step_id=str(uuid.uuid4()),
                action_type="unknown",
                params={"text": goal},
                status="pending",
                required=True
            )]
        return ActionPlan(
            plan_id=plan_id,
            user_id=user_id,
            goal=goal,
            status="pending",
            created_at=now,
            updated_at=now,
            steps=steps
        )

    def _is_single_step(self, goal: str) -> bool:
        """Detect if goal is single-step (no conjunctions and parser confident)."""
        text_lower = goal.lower()
        if any(conj in text_lower for conj in [" and ", " then ", " after ", " after that "]):
            return False
        parser = ActionParser()
        action_type, params = parser.parse(goal)
        return action_type != ActionType.UNKNOWN

    async def _llm_plan(self, goal: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Ask NIM proxy to decompose goal into steps."""
        prompt = f"""You are a planner for an AI assistant. Break down the user's goal into a sequence of executable actions.

Available actions and their required parameters:
- open_url: url (string, full URL)
- play_music: query (string, song/artist name)
- send_whatsapp: contact (string), message (string)
- check_weather: location (string, city/place)
- search_web: query (string)
- create_event: title (string), time (string, when)
- tell_joke: (no parameters needed)

Goal: "{goal}"

Guidelines:
- Order steps logically (e.g., open browser before interacting with web app).
- Only include necessary steps.
- Use the minimal number of steps.
- Ensure parameters are fully specified.
- Output ONLY a JSON object:
{{"steps": [{{"action": "action_type", "params": {{...}}}}]}}
"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.nim_url}/chat/completions",
                json={
                    "model": "claude-3-sonnet-20240229",
                    "messages": [
                        {"role": "system", "content": "You are a helpful planner."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                }
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            data = json.loads(content)
            raw_steps = data.get("steps", [])

        # Validate
        validated = []
        for raw in raw_steps:
            action = raw.get("action")
            params = raw.get("params", {})
            if action not in self.supported_actions:
                self.logger.warning(f"Planner: unsupported action {action}, skipping")
                continue
            required = self.required_params.get(action, [])
            missing = [p for p in required if p not in params or not params[p]]
            if missing:
                self.logger.warning(f"Planner: action {action} missing params {missing}, skipping")
                continue
            validated.append((action, params))
        return validated

    def _rule_split(self, goal: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Split on conjunctions and parse each segment."""
        segments = re.split(r'\b(?:and|then|after|after that)\b', goal, flags=re.IGNORECASE)
        parser = ActionParser()
        steps = []
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            action_type, params = parser.parse(seg)
            if action_type != ActionType.UNKNOWN:
                steps.append((action_type.value, params))
        return steps
