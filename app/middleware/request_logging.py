"""Request duration and status logging middleware."""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("english_guru.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and duration for each request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "HTTP request",
            extra={
                "meta": {
                    "method": request.method,
                    "path": request.url.path,
                    "statusCode": response.status_code,
                    "durationMs": duration_ms,
                }
            },
        )
        return response
