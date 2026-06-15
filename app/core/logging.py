"""Structured application logging without leaking secrets."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "idtoken",
        "id_token",
        "accesstoken",
        "access_token",
        "fcmtoken",
        "fcm_token",
        "jwt",
        "private_key",
        "firebase_private_key",
        "secret",
        "jwt_secret",
    }
)


def _sanitize_meta(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not meta:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in meta.items():
        if key.lower() in _SENSITIVE_KEYS:
            cleaned[key] = "[redacted]"
        elif isinstance(value, dict):
            cleaned[key] = _sanitize_meta(value)
        else:
            cleaned[key] = value
    return cleaned


class StructuredFormatter(logging.Formatter):
    """Emit single-line JSON log records for production readability."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        meta = getattr(record, "meta", None)
        if isinstance(meta, dict):
            payload["meta"] = _sanitize_meta(meta)
        if record.exc_info and record.exc_info[1]:
            payload["error"] = str(record.exc_info[1])
        return json.dumps(payload, default=str)


def configure_logging(*, is_production: bool) -> logging.Logger:
    """Configure root logging once at application startup."""
    root = logging.getLogger()
    if root.handlers:
        return logging.getLogger("english_guru")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO if is_production else logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    for noisy_logger in ("pymongo", "pymongo.topology", "pymongo.connection", "pymongo.serverSelection"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    return logging.getLogger("english_guru")


def log_with_meta(logger: logging.Logger, level: int, message: str, meta: dict[str, Any] | None = None) -> None:
    """Log a message with optional structured metadata."""
    logger.log(level, message, extra={"meta": meta or {}})
