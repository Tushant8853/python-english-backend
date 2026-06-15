"""Request duration and status logging middleware."""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("english_guru.http")

_SKIP_PATHS = frozenset({"/api/health", "/docs", "/redoc", "/openapi.json"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration for each request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        if request.url.path in _SKIP_PATHS:
            return response

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        message = f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)"
        if response.status_code >= 400:
            logger.warning(message)
        else:
            logger.info(message)
        return response
