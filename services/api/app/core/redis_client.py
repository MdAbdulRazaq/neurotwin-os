"""NEUROTWIN OS — Redis Client Helper"""
from app.core.config import settings
import redis.asyncio as aioredis

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis
