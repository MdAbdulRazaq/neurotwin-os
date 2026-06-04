"""
Fix orchestrator/main.py: replace services.common.* imports that break inside Docker
with self-contained equivalents using local logging_utils + stdlib.
"""
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the 4 broken external imports in one block
old = (
    "from services.common.logging_utils import setup_logging\n"
    "from services.common.fastapi_middleware import TraceMiddleware\n"
    "from services.common.http_client import get_traced_client\n"
    "from services.common.redis_events import publish_event"
)
new = (
    "from .logging_utils import setup_logging\n"
    "# TraceMiddleware: inline no-op (services.common not in Docker context)\n"
    "from starlette.middleware.base import BaseHTTPMiddleware\n"
    "class TraceMiddleware(BaseHTTPMiddleware):\n"
    "    async def dispatch(self, request, call_next):\n"
    "        return await call_next(request)\n"
    "# get_traced_client: plain httpx.AsyncClient\n"
    "from contextlib import asynccontextmanager as _acm\n"
    "@_acm\n"
    "async def get_traced_client(**kw):\n"
    "    async with httpx.AsyncClient(**kw) as c:\n"
    "        yield c\n"
    "# publish_event: direct redis publish\n"
    "async def publish_event(channel: str, data: dict, redis_client=None):\n"
    "    if redis_client:\n"
    "        import json as _j\n"
    "        await redis_client.publish(channel, _j.dumps(data))"
)

if old not in c:
    print("PATTERN NOT FOUND -- dumping existing imports:")
    for i, line in enumerate(c.split('\n')[:35], 1):
        print(f"{i:3}: {line}")
    import sys; sys.exit(1)

c = c.replace(old, new, 1)
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("PATCHED OK -- services.common imports replaced")
