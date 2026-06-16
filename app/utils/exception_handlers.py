"""Global exception handlers for consistent API error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.constants import (
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE_ENTITY,
    MESSAGES,
)
from app.core.exceptions import AppError

logger = logging.getLogger("english_guru.errors")


def _uses_wellness_envelope(request: Request) -> bool:
    path = request.url.path
    return path.startswith("/api/web-admin") or path == "/api/app/bootstrap"


def _error_content(request: Request, message: str) -> dict[str, str | bool]:
    if _uses_wellness_envelope(request):
        return {"success": False, "message": message}
    return {"status": "error", "message": message}


def _error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_content(request, message))


def _response_from_detail(
    request: Request,
    status_code: int,
    detail: Any,
) -> JSONResponse:
    if isinstance(detail, dict):
        if "status" in detail or "success" in detail:
            return JSONResponse(status_code=status_code, content=detail)
        if "message" in detail:
            return JSONResponse(
                status_code=status_code,
                content=_error_content(request, str(detail["message"])),
            )
    return _error_response(request, status_code, str(detail))


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that mirror the Node global error middleware."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= HTTP_INTERNAL_SERVER_ERROR:
            logger.error(
                f"{exc.message} ({exc.status_code})",
                extra={"meta": {"statusCode": exc.status_code}},
            )
        else:
            logger.warning(
                f"{exc.message} ({exc.status_code})",
                extra={"meta": {"statusCode": exc.status_code}},
            )
        return _error_response(request, exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        message = _first_validation_message(exc.errors())
        return _error_response(request, HTTP_UNPROCESSABLE_ENTITY, message)

    @app.exception_handler(PyMongoError)
    async def mongo_error_handler(_request: Request, exc: PyMongoError) -> JSONResponse:
        logger.error("MongoDB error", extra={"meta": {"error": str(exc)}})
        settings = get_settings()
        message = MESSAGES["ERRORS"]["INTERNAL"] if settings.is_production else "Database error"
        return _error_response(_request, HTTP_INTERNAL_SERVER_ERROR, message)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if exc.status_code == HTTP_NOT_FOUND:
            return _error_response(request, HTTP_NOT_FOUND, MESSAGES["ERRORS"]["NOT_FOUND"])
        return _response_from_detail(request, exc.status_code, exc.detail)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error",
            extra={"meta": {"error": str(exc)}},
            exc_info=exc,
        )
        settings = get_settings()
        message = MESSAGES["ERRORS"]["INTERNAL"] if settings.is_production else "An unexpected error occurred"
        return _error_response(request, HTTP_INTERNAL_SERVER_ERROR, message)


def _first_validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "Invalid request"
    first = errors[0]
    if first.get("type") == "json_invalid":
        return "Invalid JSON body"
    loc = first.get("loc", ())
    field = loc[-1] if loc else "request"
    return f"Invalid value for {field}"
