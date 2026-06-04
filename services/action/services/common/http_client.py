"""HTTP client wrapper that automatically injects traceparent headers."""

import httpx
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict

from services.common.logging_utils import get_traceparent


class TracedAsyncClient:
    """
    httpx.AsyncClient wrapper that auto-injects traceparent header
    for distributed tracing across service boundaries.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._client = httpx.AsyncClient(*args, **kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.get("headers", {}).copy()
        traceparent = get_traceparent()
        if traceparent:
            headers.setdefault("traceparent", traceparent)
        kwargs["headers"] = headers
        return await self._client.request(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)

    async def stream(self, method: str, url: str, **kwargs: Any):
        headers = kwargs.get("headers", {}).copy()
        traceparent = get_traceparent()
        if traceparent:
            headers.setdefault("traceparent", traceparent)
        kwargs["headers"] = headers
        return self._client.stream(method, url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "TracedAsyncClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)


@asynccontextmanager
async def get_traced_client(*args: Any, **kwargs: Any):
    """
    Context manager for a traced HTTP client.
    Usage: async with get_traced_client(timeout=30.0) as client:
    """
    client = TracedAsyncClient(*args, **kwargs)
    try:
        yield client
    finally:
        await client.aclose()
