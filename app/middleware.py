from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        # Reuse a caller-provided ID or generate req-<8-char-hex>.
        correlation_id = request.headers.get(
            "x-request-id",
            f"req-{uuid.uuid4().hex[:8]}"
        )
        
        bind_contextvars(correlation_id=correlation_id)
        
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)
        
        response.headers["x-request-id"] = correlation_id
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.1f}"
        
        return response
