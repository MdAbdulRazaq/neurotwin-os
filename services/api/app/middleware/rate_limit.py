"""
NEUROTWIN OS — Rate Limit Middleware
Redis sliding window counter per user/IP.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("neurotwin.middleware.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period

    async def dispatch(self, request, call_next):
        redis = getattr(request.app.state, "redis", None)
        if not redis:
            return await call_next(request)

        # Key by user_id if authenticated, else IP
        user_id = getattr(request.state, "user_id", None)
        identifier = user_id or request.client.host or "unknown"
        key = f"rl:{identifier}"
        now = time.time()
        window_start = now - self.period

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self.period)
        results = await pipe.execute()

        count = results[2]
        if count > self.calls:
            retry_after = int(self.period - (now - window_start))
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(self.calls)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.calls - count))
        return response
