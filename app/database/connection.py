"""Async MongoDB client using Motor."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger("english_guru.database")

_client: AsyncIOMotorClient[Any] | None = None
_database: AsyncIOMotorDatabase[Any] | None = None


async def connect_database() -> bool:
    """
    Establish the Motor client connection.

    Returns True when connected, False when unavailable (server may still serve health).
  """
    global _client, _database
    settings = get_settings()

    if _client is not None:
        return _database is not None

    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        _database = _client[_resolve_database_name(settings.mongodb_uri, settings.mongodb_db_name)]
        await _client.admin.command("ping")
        logger.info("MongoDB connected")
        return True
    except Exception as exc:
        logger.warning(
            "MongoDB unavailable; server is running without persistence. Check MONGODB_URI and your database process.",
            extra={"meta": {"error": str(exc)}},
        )
        if _client is not None:
            _client.close()
        _client = None
        _database = None
        return False


async def close_database() -> None:
    """Close the Motor client on application shutdown."""
    global _client, _database
    if _client is not None:
        _client.close()
        logger.info("MongoDB disconnected")
    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase[Any]:
    """Return the active database handle or raise when persistence is unavailable."""
    if _database is None:
        raise RuntimeError("MongoDB is not connected")
    return _database


def _resolve_database_name(uri: str, override: str | None) -> str:
    """Resolve DB name from env override, URI path, or Mongoose-compatible default."""
    if override and override.strip():
        return override.strip()
    parsed = urlparse(uri)
    path = parsed.path.lstrip("/")
    if path:
        return path.split("?")[0]
    return "test"
