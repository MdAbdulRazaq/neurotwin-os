"""
User Profile System — Comprehensive user modeling for NEUROTWIN.
Aggregates traits, preferences, emotional patterns, behavior patterns, and decision patterns from Neo4j and Redis.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from neo4j import AsyncGraphDatabase
import os

logger = logging.getLogger("agents.user_profile")

# === Pydantic Models ===

class TraitScore(BaseModel):
    trait: str
    score: float = Field(ge=0.0, le=1.0, description="Normalized strength of this trait (0-1)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this trait assessment")
    last_updated: datetime

class ActionPreference(BaseModel):
    action: str
    weight: float = Field(ge=0.0, le=1.0, description="Preference weight based on usage and acceptance")
    count: int = Field(description="Number of times this action was performed")
    acceptance_rate: float = Field(ge=0.0, le=1.0, description="Proportion of successful outcomes")
    last_seen: datetime

class EmotionalPattern(BaseModel):
    emotion: str
    average_intensity: float = Field(ge=0.0, le=1.0)
    frequency: int = Field(description="Number of occurrences in analyzed period")
    triggers: List[str] = Field(default_factory=list, description="What tends to trigger this emotion")
    associated_actions: List[str] = Field(default_factory=list, description="Actions often taken in this emotion")

class EmotionalBaseline(BaseModel):
    typical_emotion: str
    volatility: float = Field(ge=0.0, le=1.0, description="How much emotional intensity varies")
    recovery_time_minutes: float = Field(description="Average time to return to baseline after a spike")
    stress_triggers: List[str] = Field(default_factory=list)
    last_updated: datetime

class BehaviorPattern(BaseModel):
    pattern_type: str  # "routine", "engagement", "interaction"
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    metrics: Dict[str, float] = Field(default_factory=dict, description="Quantitative measures of this pattern")
    last_observed: datetime

class Habit(BaseModel):
    name: str
    frequency: str  # "daily", "weekly", "monthly", "occasional"
    typical_time: Optional[str] = None
    context: List[str] = Field(default_factory=list)
    strength: float = Field(ge=0.0, le=1.0)
    last_occurrence: datetime

class DecisionPattern(BaseModel):
    style: str  # "analytical", "intuitive", "habitual", "social"
    risk_tolerance: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0, description="How consistently the user follows through")
    influencing_factors: List[str] = Field(default_factory=list)
    decision_speed: str = Field(default="moderate")  # "fast", "moderate", "slow"

class UserProfile(BaseModel):
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    profile_version: int = 1

    # Core personality
    personality_traits: List[TraitScore] = Field(default_factory=list)
    communication_style: Optional[str] = None

    # Preferences
    preferred_actions: List[ActionPreference] = Field(default_factory=list)
    time_preferences: Dict[str, float] = Field(default_factory=dict)  # hour (0-23) -> score
    topic_interests: Dict[str, float] = Field(default_factory=dict)  # topic -> interest level

    # Emotional
    emotional_baseline: Optional[EmotionalBaseline] = None
    emotional_patterns: List[EmotionalPattern] = Field(default_factory=list)
    current_emotion: Optional[Dict[str, Any]] = None

    # Behavior
    behavior_patterns: List[BehaviorPattern] = Field(default_factory=list)
    habits: List[Habit] = Field(default_factory=list)
    engagement_score: float = 0.5

    # Decision
    decision_patterns: List[DecisionPattern] = Field(default_factory=list)

    # Learning characteristics
    adaptation_speed: float = 0.5  # How quickly the user responds to suggestions
    feedback_responsiveness: float = 0.5

    # Summary
    primary_trait: Optional[str] = None
    dominant_decision_style: Optional[str] = None
    personalization_suggestions: List[str] = Field(default_factory=list)


class UserProfileBuilder:
    """Builds comprehensive UserProfile from Neo4j graph data and Redis patterns."""

    def __init__(self, neo4j_driver, redis_client=None):
        self.driver = neo4j_driver
        self.redis = redis_client
        self.logger = logging.getLogger("agents.user_profile.builder")

    async def build(self, user_id: str, lookback_days: int = 30) -> UserProfile:
        """Main entry point: aggregates all data and returns a UserProfile."""
        profile = UserProfile(user_id=user_id)

        try:
            async with self.driver.session() as session:
                # Run all queries in parallel within the session
                tasks = [
                    self._fetch_traits(session, user_id),
                    self._fetch_action_preferences(session, user_id),
                    self._fetch_emotion_patterns(session, user_id, lookback_days),
                    self._fetch_performed_actions(session, user_id),
                ]
                traits, prefs, emotions, performed = await asyncio.gather(*tasks)
                redis_patterns = await self._fetch_redis_patterns(user_id) if self.redis else {}

                # Build profile sections
                await self._build_personality(profile, traits)
                await self._build_preferences(profile, prefs, performed, redis_patterns)
                await self._build_emotional_profile(profile, emotions)
                await self._build_behavior_profile(profile, performed)
                await self._build_decision_profile(profile, performed)
                await self._detect_habits_from_performance(profile, performed)
                await self._compute_summary(profile)

        except Exception as e:
            self.logger.error(f"Profile build failed for user {user_id}: {e}", exc_info=True)
            # Return minimal profile on error
            profile.personality_traits = []

        profile.updated_at = datetime.utcnow()
        return profile

    async def _fetch_traits(self, session, user_id: str) -> List[Dict]:
        """Fetch HAS_TRAIT relationships."""
        result = await session.run(
            """MATCH (u:User {id: $uid})- [r:HAS_TRAIT] -> (t:Trait)
               RETURN t.name as name, r.value as value, r.timestamp as ts
               ORDER BY r.timestamp DESC
            """,
            uid=user_id
        )
        return [dict(rec) async for rec in result]

    async def _fetch_action_preferences(self, session, user_id: str) -> List[Dict]:
        """Fetch PREFERS relationships."""
        result = await session.run(
            """MATCH (u:User {id: $uid})- [r:PREFERS] -> (a:Action)
               RETURN a.name as action, r.count as count, r.timestamp as ts
               ORDER BY r.timestamp DESC
            """,
            uid=user_id
        )
        return [dict(rec) async for rec in result]

    async def _fetch_emotion_patterns(self, session, user_id: str, days: int) -> List[Dict]:
        """Fetch emotion patterns within lookback period."""
        result = await session.run(
            """MATCH (u:User {id: $uid})-[:HAS_EMOTION]->(e:EmotionPattern)
               WHERE e.timestamp > datetime() - duration({days: $days})
               RETURN e.emotion as emotion, e.intensity as intensity,
                      e.timestamp as ts
               ORDER BY e.ts
            """,
            uid=user_id, days=days
        )
        return [dict(rec) async for rec in result]

    async def _fetch_performed_actions(self, session, user_id: str) -> List[Dict]:
        """Fetch PERFORMED relationships from learning agent."""
        result = await session.run(
            """MATCH (u:User {id: $uid})- [r:PERFORMED] -> (a:Action)
               RETURN a.name as action, r.count as count,
                      r.acceptance_rate as acceptance_rate,
                      r.weight as weight, r.last_seen as last_seen
            """,
            uid=user_id
        )
        return [dict(rec) async for rec in result]

    async def _fetch_redis_patterns(self, user_id: str) -> Dict[str, List[Dict]]:
        """Fetch detailed patterns from Redis hash neurotwin:patterns."""
        patterns = {}
        if not self.redis:
            return patterns
        try:
            all_data = await self.redis.hgetall("neurotwin:patterns")
            for key, val in all_data.items():
                if key.startswith(f"{user_id}:"):
                    parts = key.split(":")
                    if len(parts) == 4:
                        _, tod, emotion, action = parts
                        try:
                            data = json.loads(val)
                            patterns.setdefault(action, []).append({
                                "time_of_day": int(tod) if tod.isdigit() else 12,
                                "emotion": emotion,
                                "weight": data.get("weight", 0.5),
                                "count": data.get("count", 0)
                            })
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.warning(f"Redis patterns fetch failed: {e}")
        return patterns

    # --- Build methods ---

    async def _build_personality(self, profile: UserProfile, traits: List[Dict]):
        """Construct personality traits from HAS_TRAIT."""
        if not traits:
            profile.communication_style = "neutral"
            return

        # Map trait values to scores (current system stores "positive", "neutral", "stressed")
        value_scores = {"positive": 0.8, "neutral": 0.5, "stressed": 0.2}

        # Deduplicate by trait name, keep most recent
        latest_traits: Dict[str, Dict] = {}
        for t in traits:
            name = t["name"]
            if name not in latest_traits or t["ts"] > latest_traits[name]["ts"]:
                latest_traits[name] = t

        for name, data in latest_traits.items():
            value = data.get("value", "neutral")
            score = value_scores.get(value, 0.5)
            ts = data.get("ts")
            if isinstance(ts, datetime):
                last_updated = ts
            else:
                try:
                    last_updated = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except:
                    last_updated = datetime.utcnow()

            profile.personality_traits.append(
                TraitScore(
                    trait=name,
                    score=score,
                    confidence=0.8,
                    last_updated=last_updated
                )
            )

        # Primary trait
        if profile.personality_traits:
            primary = max(profile.personality_traits, key=lambda t: t.score)
            profile.primary_trait = primary.trait
            # Infer communication style
            if primary.trait == "positive":
                profile.communication_style = "warm"
            elif primary.trait == "stressed":
                profile.communication_style = "supportive"
            else:
                profile.communication_style = "neutral"

    async def _build_preferences(self, profile: UserProfile, prefers: List[Dict], performed: List[Dict], redis_patterns: Dict = None):
        """Build action preferences by merging PREFERS and PERFORMED and time patterns."""
        action_data: Dict[str, Dict] = {}

        # From PREFERS
        for p in prefers:
            act = p["action"]
            action_data.setdefault(act, {"count": 0, "last_used_prefers": None, "last_used_performed": None, "acceptance_rate": 0.5})
            action_data[act]["count"] += p.get("count", 1)
            ts = p.get("ts")
            if ts:
                last_dt = self._parse_ts(ts)
                if last_dt and (action_data[act]["last_used_prefers"] is None or last_dt > action_data[act]["last_used_prefers"]):
                    action_data[act]["last_used_prefers"] = last_dt

        # From PERFORMED
        for p in performed:
            act = p["action"]
            data = action_data.setdefault(act, {"count": 0, "last_used_prefers": None, "last_used_performed": None, "acceptance_rate": 0.5})
            data["count"] += p.get("count", 0) or 0
            data["weight"] = p.get("weight", 0.5)
            data["acceptance_rate"] = p.get("acceptance_rate", 0.5)
            ts = p.get("last_seen")
            if ts:
                last_dt = self._parse_ts(ts)
                if last_dt and (data["last_used_performed"] is None or last_dt > data["last_used_performed"]):
                    data["last_used_performed"] = last_dt

        # Build ActionPreference list sorted by weight
        for act, data in action_data.items():
            last_used = data.get("last_used_performed") or data.get("last_used_prefers") or datetime.utcnow()
            profile.preferred_actions.append(
                ActionPreference(
                    action=act,
                    weight=data.get("weight", min(1.0, data["count"] * 0.1)),
                    count=data["count"],
                    acceptance_rate=data.get("acceptance_rate", 0.5),
                    last_seen=last_used
                )
            )

        profile.preferred_actions.sort(key=lambda x: x.weight, reverse=True)

        # Incorporate time preferences from Redis patterns if available
        if redis_patterns:
            time_scores: Dict[int, float] = {}
            for action, entries in redis_patterns.items():
                for entry in entries:
                    hour = entry["time_of_day"]
                    weight = entry.get("weight", 0.5)
                    time_scores[hour] = time_scores.get(hour, 0) + weight
            if time_scores:
                max_score = max(time_scores.values())
                profile.time_preferences = {str(h): round(score/max_score, 3) for h, score in sorted(time_scores.items())}

    def _parse_ts(self, ts) -> Optional[datetime]:
        """Parse Neo4j datetime or string to datetime."""
        if isinstance(ts, datetime):
            return ts
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except:
            return None

    async def _build_emotional_profile(self, profile: UserProfile, emotions: List[Dict]):
        """Analyze emotion patterns and compute baseline."""
        if not emotions:
            profile.emotional_baseline = EmotionalBaseline(
                typical_emotion="neutral",
                volatility=0.2,
                recovery_time_minutes=15.0,
                stress_triggers=[],
                last_updated=datetime.utcnow()
            )
            return

        # Group by emotion
        by_emotion: Dict[str, List[float]] = {}
        for e in emotions:
            emo = e["emotion"]
            intensity = e.get("intensity", 0.5)
            by_emotion.setdefault(emo, []).append(intensity)

        # Create emotional patterns
        for emotion, intensities in by_emotion.items():
            avg_int = sum(intensities) / len(intensities)
            profile.emotional_patterns.append(
                EmotionalPattern(
                    emotion=emotion,
                    average_intensity=avg_int,
                    frequency=len(intensities),
                    triggers=[],
                    associated_actions=[]
                )
            )

        # Determine baseline
        baseline_emo = max(by_emotion.items(), key=lambda x: len(x[1]))[0] if by_emotion else "neutral"

        # Compute volatility (std dev)
        all_ints = [i for ints in by_emotion.values() for i in ints]
        if len(all_ints) > 1:
            mean = sum(all_ints) / len(all_ints)
            variance = sum((i - mean)**2 for i in all_ints) / len(all_ints)
            volatility = variance ** 0.5
        else:
            volatility = 0.2

        # Stress triggers (keywords)
        stress_keywords = {"angry", "sad", "fear", "anxious", "stressed"}
        stress_triggers = [emo for emo in stress_keywords if emo in by_emotion]

        profile.emotional_baseline = EmotionalBaseline(
            typical_emotion=baseline_emo,
            volatility=volatility,
            recovery_time_minutes=15.0,
            stress_triggers=stress_triggers,
            last_updated=datetime.utcnow()
        )

    async def _build_behavior_profile(self, profile: UserProfile, performed: List[Dict]):
        """Derive behavior patterns from action performance."""
        if not performed:
            return

        total_actions = sum(p.get("count", 0) for p in performed)
        if total_actions == 0:
            return

        unique_actions = len(performed)
        diversity_score = min(1.0, unique_actions / 20)

        acceptance_rates = [p.get("acceptance_rate", 0.5) for p in performed if "acceptance_rate" in p]
        avg_acceptance = sum(acceptance_rates) / len(acceptance_rates) if acceptance_rates else 0.5

        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_count = sum(p.get("count", 0) for p in performed if self._parse_ts(p.get("last_seen")) and self._parse_ts(p["last_seen"]) > recent_cutoff)
        engagement_score = min(1.0, (recent_count / 50) + (avg_acceptance * 0.5))
        profile.engagement_score = max(0.1, engagement_score)

        if diversity_score > 0.6 and avg_acceptance > 0.7:
            pattern_type = "exploratory"
            description = "User tries many different actions with high success rate"
        elif diversity_score < 0.3:
            pattern_type = "focused"
            description = "User sticks to a small set of actions"
        else:
            pattern_type = "balanced"
            description = "User has moderate variety in actions"

        profile.behavior_patterns.append(
            BehaviorPattern(
                pattern_type="action_diversity",
                description=description,
                confidence=min(1.0, total_actions / 100),
                metrics={
                    "diversity": diversity_score,
                    "avg_acceptance": avg_acceptance,
                    "total_actions": total_actions
                },
                last_observed=datetime.utcnow()
            )
        )

    async def _build_decision_profile(self, profile: UserProfile, performed: List[Dict]):
        """Analyze decision-making style from action weights and acceptance."""
        if not performed:
            profile.decision_patterns.append(
                DecisionPattern(
                    style="undetermined",
                    risk_tolerance=0.5,
                    consistency=0.0,
                    influencing_factors=[],
                    decision_speed="unknown"
                )
            )
            return

        weights = [p.get("weight", 0.5) for p in performed]
        acceptance_rates = [p.get("acceptance_rate", 0.5) for p in performed]
        avg_weight = sum(weights) / len(weights) if weights else 0.5
        avg_acceptance = sum(acceptance_rates) / len(acceptance_rates) if acceptance_rates else 0.5

        consistency = avg_acceptance
        risk_tolerance = avg_weight

        unique_actions = len(performed)
        if unique_actions > 10 and consistency > 0.7:
            style = "exploratory"
            decision_speed = "moderate"
        elif unique_actions <= 5 and consistency > 0.8:
            style = "habitual"
            decision_speed = "fast"
        elif consistency < 0.6:
            style = "hesitant"
            decision_speed = "slow"
        else:
            style = "balanced"
            decision_speed = "moderate"

        factors = ["past_success", "personal_preference"]
        if avg_weight > 0.7:
            factors.append("confidence")
        if len(performed) > 20:
            factors.append("learned_patterns")

        profile.decision_patterns.append(
            DecisionPattern(
                style=style,
                risk_tolerance=risk_tolerance,
                consistency=consistency,
                influencing_factors=factors,
                decision_speed=decision_speed
            )
        )
        profile.dominant_decision_style = style

    async def _detect_habits_from_performance(self, profile: UserProfile, performed: List[Dict]):
        """Detect habits from action performance patterns."""
        for p in performed:
            count = p.get("count", 0)
            weight = p.get("weight", 0)
            if count > 5 or weight > 0.7:
                action = p["action"]
                profile.habits.append(
                    Habit(
                        name=f"uses_{action}",
                        frequency="regular",
                        typical_time=None,
                        context=[],
                        strength=min(1.0, count * 0.1 + weight * 0.5),
                        last_occurrence=self._parse_ts(p.get("last_seen")) or datetime.utcnow()
                    )
                )

    async def _compute_summary(self, profile: UserProfile):
        """Compute derived summary fields and suggestions."""
        if profile.personality_traits:
            profile.primary_trait = max(profile.personality_traits, key=lambda t: t.score).trait

        suggestions = []

        if profile.engagement_score < 0.4:
            suggestions.append("User has low engagement; use more interactive prompts")
        if profile.emotional_baseline and profile.emotional_baseline.volatility > 0.6:
            suggestions.append("High emotional volatility detected; use calming, steady tone")
        if profile.decision_patterns and profile.decision_patterns[0].style == "habitual":
            suggestions.append("User prefers routine; suggest familiar actions and respect timing")
        if profile.decision_patterns and profile.decision_patterns[0].style == "exploratory":
            suggestions.append("User enjoys exploration; occasionally suggest new options")
        if any(h.strength > 0.8 for h in profile.habits):
            suggestions.append("Strong habits detected; align suggestions with routine")

        profile.personalization_suggestions = suggestions

        profile.adaptation_speed = 0.5
        profile.feedback_responsiveness = 0.5
