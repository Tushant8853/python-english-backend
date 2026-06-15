"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.connection import close_database, connect_database
from app.middleware.request_logging import RequestLoggingMiddleware
from app.utils.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Connect to MongoDB on startup; close on shutdown."""
    await connect_database()
    yield
    await close_database()


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware and routes."""
    settings = get_settings()
    logger = configure_logging(is_production=settings.is_production)

    app = FastAPI(
        title="English Guru API",
        description="Production FastAPI backend for the English Guru mobile application.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")

    logger.info(
        "English Guru FastAPI application configured",
        extra={"meta": {"environment": settings.environment, "port": settings.port}},
    )
    return app


app = create_app()
