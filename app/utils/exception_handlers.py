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
from app.core.constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR, HTTP_NOT_FOUND, MESSAGES
from app.core.exceptions import AppError

logger = logging.getLogger("english_guru.errors")


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "error", "message": message})


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that mirror the Node global error middleware."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            f"{exc.message} ({exc.status_code})",
            extra={"meta": {"statusCode": exc.status_code}},
        )
        return _error_response(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        message = _first_validation_message(exc.errors())
        return _error_response(HTTP_BAD_REQUEST, message)

    @app.exception_handler(PyMongoError)
    async def mongo_error_handler(_request: Request, exc: PyMongoError) -> JSONResponse:
        logger.error("MongoDB error", extra={"meta": {"error": str(exc)}})
        settings = get_settings()
        message = MESSAGES["ERRORS"]["INTERNAL"] if settings.is_production else str(exc)
        return _error_response(HTTP_INTERNAL_SERVER_ERROR, message)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if exc.status_code == HTTP_NOT_FOUND:
            return _error_response(HTTP_NOT_FOUND, MESSAGES["ERRORS"]["NOT_FOUND"])
        if isinstance(exc.detail, dict) and "status" in exc.detail and "message" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return _error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error",
            extra={"meta": {"error": str(exc)}},
            exc_info=exc,
        )
        settings = get_settings()
        message = MESSAGES["ERRORS"]["INTERNAL"] if settings.is_production else str(exc)
        return _error_response(HTTP_INTERNAL_SERVER_ERROR, message)


def _first_validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "Invalid request"
    first = errors[0]
    if first.get("type") == "json_invalid":
        return "Invalid JSON body"
    loc = first.get("loc", ())
    field = loc[-1] if loc else "request"
    return f"Invalid value for {field}"
