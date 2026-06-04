"""
NEUROTWIN OS — Analytics Router
Mood timeline, topic frequency, engagement score.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.database import get_db, Session as DBSession, ConversationMessage as DBMessage, EmotionEvent as DBEmotionEvent
from app.core.schemas import AnalyticsSummaryResponse, MoodTimelineResponse
from app.middleware.auth import get_current_user

import re
from collections import defaultdict

# Common English stop words for topic extraction
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might",
    "must", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "this", "that", "these",
    "those", "there", "here", "what", "which", "who", "where", "when", "why", "how",
    "all", "some", "any", "no", "not", "only", "just", "also", "very", "too", "so",
    "if", "then", "else", "because", "since", "while", "as", "until", "before", "after",
    "during", "about", "above", "below", "between", "among", "from", "into", "out",
    "up", "down", "off", "over", "under", "again", "further", "once", "more", "most",
    "such", "each", "few", "many", "much", "other", "another", "both", "same", "so",
    "than", "too", "very", "s", "t", "just", "don", "should", "now", "d", "ll", "m",
    "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn",
    "haven", "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn", "ve", "ll", "m", "aren't", "couldn't", "didn't", "doesn't", "hadn't",
    "hasn't", "haven't", "isn't", "mightn't", "mustn't", "needn't", "shan't", "shouldn't",
    "wasn't", "weren't", "won't", "wouldn't"
}

router = APIRouter()
logger = logging.getLogger("neurotwin.analytics")


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    request: Request,
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pre-computed or freshly computed analytics summary."""
    user_id = current_user["id"]
    redis = request.app.state.redis

    # Check cache
    cache_key = f"analytics:{user_id}:{days}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # total_sessions (within date range)
    sessions_q = select(func.count()).select_from(DBSession).where(
        and_(
            DBSession.user_id == user_id,
            DBSession.created_at >= start_date,
        )
    )
    total_sessions = (await db.execute(sessions_q)).scalar_one() or 0

    # total_messages within date range
    messages_q = select(func.count()).select_from(DBMessage).join(
        DBSession, DBMessage.session_id == DBSession.id
    ).where(
        and_(
            DBSession.user_id == user_id,
            DBMessage.created_at >= start_date,
        )
    )
    total_messages = (await db.execute(messages_q)).scalar_one() or 0

    # avg_session_length_minutes (only for completed sessions)
    avg_duration_q = select(
        func.avg(
            func.extract('epoch', DBSession.ended_at - DBSession.created_at) / 60.0
        )
    ).where(
        and_(
            DBSession.user_id == user_id,
            DBSession.created_at >= start_date,
            DBSession.ended_at.isnot(None),
        )
    )
    avg_seconds = (await db.execute(avg_duration_q)).scalar_one()
    avg_session_length_minutes = (avg_seconds or 0) if avg_seconds is None else float(avg_seconds)

    # mood_timeline: Get emotion events within date range
    mood_events_q = select(
        DBEmotionEvent.created_at,
        DBEmotionEvent.emotion,
        DBEmotionEvent.intensity,
        DBEmotionEvent.session_id,
    ).where(
        and_(
            DBEmotionEvent.user_id == user_id,
            DBEmotionEvent.created_at >= start_date,
        )
    ).order_by(DBEmotionEvent.created_at)
    mood_results = (await db.execute(mood_events_q)).all()

    mood_timeline = [
        {
            "timestamp": row.created_at,
            "emotion": row.emotion,
            "intensity": float(row.intensity),
            "session_id": str(row.session_id) if row.session_id else None,
        }
        for row in mood_results
    ]

    # top_topics: Extract from user messages content using word frequency
    messages_data_q = select(
        DBMessage.content,
        DBMessage.created_at,
    ).join(
        DBSession, DBMessage.session_id == DBSession.id
    ).where(
        and_(
            DBSession.user_id == user_id,
            DBMessage.created_at >= start_date,
            DBMessage.role == "user",
        )
    )
    messages_data = (await db.execute(messages_data_q)).all()

    word_counts = defaultdict(int)
    word_last_mentioned = {}
    for row in messages_data:
        content = row.content or ""
        created_at = row.created_at
        words = re.findall(r'\b\w+\b', content.lower())
        for word in words:
            if len(word) < 3 or word in STOP_WORDS or word.isdigit():
                continue
            word_counts[word] += 1
            if word not in word_last_mentioned or created_at > word_last_mentioned[word]:
                word_last_mentioned[word] = created_at

    top_topics = [
        {"topic": w, "count": c, "last_mentioned": word_last_mentioned[w]}
        for w, c in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]

    # engagement_score
    messages_per_day = total_messages / days if days > 0 else 0
    sessions_per_day = total_sessions / days if days > 0 else 0
    engagement_score = min(1.0, (messages_per_day / 5.0) * 0.7 + (sessions_per_day / 1.0) * 0.3)

    result = {
        "user_id": str(user_id),
        "period_days": days,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "avg_session_length_minutes": avg_session_length_minutes,
        "mood_timeline": mood_timeline,
        "top_topics": top_topics,
        "engagement_score": engagement_score,
    }

    response = AnalyticsSummaryResponse(**result)

    await redis.setex(cache_key, 300, response.json())

    return response


@router.get("/mood")
async def get_mood_timeline(
    request: Request,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return mood timeline for charting."""
    user_id = current_user["id"]
    redis = request.app.state.redis

    cache_key = f"mood:{user_id}:{days}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Query emotion events
    stmt = select(
        DBEmotionEvent.created_at,
        DBEmotionEvent.emotion,
        DBEmotionEvent.intensity,
        DBEmotionEvent.session_id,
    ).where(
        and_(
            DBEmotionEvent.user_id == user_id,
            DBEmotionEvent.created_at >= start_date,
        )
    ).order_by(DBEmotionEvent.created_at)

    results = (await db.execute(stmt)).all()

    data_points = [
        {
            "timestamp": row.created_at,
            "emotion": row.emotion,
            "intensity": float(row.intensity),
            "session_id": str(row.session_id) if row.session_id else None,
        }
        for row in results
    ]

    # Compute dominant_emotion and average_intensity
    if data_points:
        emotion_counts = {}
        total_intensity = 0.0
        for point in data_points:
            emo = point["emotion"]
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
            total_intensity += point["intensity"]
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        average_intensity = total_intensity / len(data_points)
    else:
        dominant_emotion = "neutral"
        average_intensity = 0.0

    result = {
        "user_id": str(user_id),
        "period_days": days,
        "data_points": data_points,
        "dominant_emotion": dominant_emotion,
        "average_intensity": round(average_intensity, 3),
    }

    response = MoodTimelineResponse(**result)

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, response.json())

    return response
