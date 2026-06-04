"""FastAPI middleware for distributed tracing."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from services.common.logging_utils import (
    set_traceparent,
    get_traceparent,
    set_trace_id,
    set_span_id,
    generate_trace_id,
    generate_span_id,
    set_parent_span_id,
)


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Extract traceparent from incoming requests and set context.
    Also inject traceparent into response headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Extract traceparent from headers
        traceparent = request.headers.get("traceparent")

        if traceparent:
            set_traceparent(traceparent)
            # Extract parent span ID from incoming traceparent for proper hierarchy
            try:
                parts = traceparent.split("-")
                if len(parts) == 4:
                    _, _, parent_span, _ = parts
                    set_parent_span_id(parent_span)
            except Exception:
                pass
        else:
            # No incoming trace, generate new trace
            trace_id = generate_trace_id()
            set_trace_id(trace_id)

        # Create new span ID for this request
        span_id = generate_span_id()
        set_span_id(span_id)

        response = await call_next(request)

        # Add traceparent to response headers so clients can chain
        response_traceparent = get_traceparent()
        if response_traceparent:
            response.headers["traceparent"] = response_traceparent

        return response
