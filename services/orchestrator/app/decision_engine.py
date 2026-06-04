"""
Decision Engine — Pre-response reasoning for NEUROTWIN.
Analyzes user state and suggests optimal response strategies before LLM call.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("orchestrator.decision_engine")

class DecisionEngine:
    def __init__(self):
        pass

    async def analyze(self, profile: Dict[str, Any], context: Dict[str, Any], message: str) -> Dict[str, Any]:
        """
        Analyze user state and produce decision guidance.

        Returns:
            {
                "insights": [...],
                "recommended_actions": [...],
                "reasoning": [...],
                "confidence": float
            }
        """
        analysis = {
            "insights": [],
            "recommended_actions": [],
            "reasoning": [],
            "confidence": 0.5
        }

        # Extract profile components
        primary_trait = profile.get("primary_trait")
        decision_style = profile.get("dominant_decision_style")
        habits = profile.get("habits", [])
        preferred_actions = profile.get("preferred_actions", [])
        emotional_baseline = profile.get("emotional_baseline", {})
        engagement = profile.get("engagement_score", 0.5)

        # Extract current context
        current_emotion = context.get("emotion", "neutral")
        intent = context.get("intent", "CHAT")
        time_of_day = context.get("time_of_day", datetime.utcnow().hour)

        # Insight 1: Emotion vs baseline
        typical = emotional_baseline.get("typical_emotion", "neutral")
        if current_emotion != typical:
            analysis["insights"].append(f"User is feeling {current_emotion} (baseline: {typical})")
            analysis["reasoning"].append("Deviation from baseline indicates topical relevance.")

        # Insight 2: Time-based habits
        for habit in habits:
            habit_name = habit.get("name", "")
            typical_time = habit.get("typical_time")
            if typical_time:
                try:
                    if isinstance(typical_time, str) and typical_time.isdigit():
                        habit_hour = int(typical_time)
                        if abs(habit_hour - time_of_day) <= 1:
                            action = habit_name.replace("uses_", "")
                            analysis["insights"].append(f"Habit: {action} around this hour")
                            analysis["recommended_actions"].append(action)
                except:
                    pass

        # Insight 3: Preferred actions matching topic
        message_lower = message.lower()
        for act in preferred_actions[:5]:
            action = act["action"]
            if action in message_lower:
                analysis["insights"].append(f"User mentioned {action} which they prefer")
                analysis["recommended_actions"].append(action)

        # Insight 4: Engagement level
        if engagement < 0.4:
            analysis["insights"].append("Low engagement")
            analysis["recommended_actions"].append("ask_engaging_question")
        elif engagement > 0.8:
            analysis["insights"].append("High engagement")
            analysis["recommended_actions"].append("continue_current_topic")

        # Fallback
        if not analysis["recommended_actions"]:
            analysis["recommended_actions"].append("explore_preferences")

        # Deduplicate and limit
        analysis["recommended_actions"] = list(set(analysis["recommended_actions"]))[:3]
        analysis["confidence"] = min(0.9, 0.5 + len(analysis["insights"]) * 0.1)

        return analysis
