"""Redis event publishing with trace context propagation."""

import json
import logging
from typing import Any, Dict

import redis.asyncio as aioredis

from services.common.logging_utils import get_trace_id, get_span_id

logger = logging.getLogger(__name__)


async def publish_event(channel: str, data: Dict[str, Any], redis_client: aioredis.Redis = None, redis: aioredis.Redis = None) -> None:
    """
    Publish an event to a Redis channel with trace context.

    The event is wrapped in a standard envelope containing version,
    trace_id, span_id, and the original data.

    Args:
        redis: Redis client instance
        channel: Channel name to publish to
        data: Event payload (will be stored under 'data' key)
    """
    trace_id = get_trace_id()
    span_id = get_span_id()

    event = {
        "version": "v1",
        "trace_id": trace_id or "none",
        "span_id": span_id or "none",
        "channel": channel,
        "data": data,
    }

    client = redis_client or redis
    try:
        await client.publish(channel, json.dumps(event))
    except Exception as e:
        logger.exception("Failed to publish event to channel %s: %s", channel, e)
        raise


async def create_redis_event(channel: str, data: Dict[str, Any], trace_id: str = None, span_id: str = None) -> Dict[str, Any]:
    """
    Create an event envelope without publishing.
    Useful for testing or when you need to construct the event manually.

    Args:
        channel: Channel name
        data: Event payload
        trace_id: Optional trace ID (uses context if not provided)
        span_id: Optional span ID (uses context if not provided)

    Returns:
        Event envelope dictionary
    """
    from services.common.logging_utils import get_trace_id as _get_trace_id, get_span_id as _get_span_id

    tid = trace_id or _get_trace_id() or "none"
    sid = span_id or _get_span_id() or "none"

    return {
        "version": "v1",
        "trace_id": tid,
        "span_id": sid,
        "channel": channel,
        "data": data,
    }
