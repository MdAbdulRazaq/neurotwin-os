from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import uuid
import time

@dataclass
class PlanStep:
    step_id: str
    action_type: str
    params: Dict[str, Any]
    status: str  # "pending" | "running" | "success" | "failed" | "skipped"
    retry_count: int = 0
    max_retries: int = 3
    required: bool = True
    result: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict] = None
    continue_on_error: bool = False

@dataclass
class ActionPlan:
    plan_id: str
    user_id: str
    goal: str
    status: str  # "pending" | "running" | "completed" | "failed" | "cancelled"
    created_at: float
    updated_at: float
    steps: List[PlanStep]
    current_step_index: int = 0
