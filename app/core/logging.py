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

_NOISY_LOGGERS = (
    "pymongo",
    "pymongo.topology",
    "pymongo.connection",
    "pymongo.serverSelection",
    "urllib3",
    "urllib3.connectionpool",
    "cachecontrol",
    "cachecontrol.controller",
    "httpx",
    "httpcore",
    "watchfiles",
    "google",
    "google.auth",
    "googleapiclient",
    "firebase_admin",
    "uvicorn.access",
)

_RESET = "\033[0m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"

_LEVEL_COLORS = {
    "INFO": _GREEN,
    "WARNING": _YELLOW,
    "ERROR": _RED,
    "CRITICAL": _RED,
}


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


def _format_meta(meta: dict[str, Any] | None) -> str:
    if not meta:
        return ""
    sanitized = _sanitize_meta(meta) or {}
    parts = [f"{key}={value}" for key, value in sanitized.items()]
    return f" ({', '.join(parts)})" if parts else ""


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


class DevConsoleFormatter(logging.Formatter):
    """Readable single-line logs for local development."""

    def format(self, record: logging.LogRecord) -> str:
        meta = getattr(record, "meta", None)
        meta_suffix = _format_meta(meta) if isinstance(meta, dict) else ""
        line = f"{record.levelname:5} {record.name}: {record.getMessage()}{meta_suffix}"
        if sys.stdout.isatty():
            color = _LEVEL_COLORS.get(record.levelname, "")
            if color:
                return f"{color}{line}{_RESET}"
        return line


def configure_logging(*, is_production: bool) -> logging.Logger:
    """Configure root logging once at application startup."""
    root = logging.getLogger()
    if root.handlers:
        return logging.getLogger("english_guru")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter() if is_production else DevConsoleFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    return logging.getLogger("english_guru")
