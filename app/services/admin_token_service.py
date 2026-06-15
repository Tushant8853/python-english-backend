"""JWT issue and verification for web admin dashboard (separate from mobile access tokens)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.constants import HTTP_SERVICE_UNAVAILABLE, HTTP_UNAUTHORIZED
from app.core.exceptions import AppError

ALGORITHM = "HS256"
ADMIN_TOKEN_EXPIRY = timedelta(hours=12)


@dataclass(frozen=True)
class WebAdminTokenPayload:
    username: str
    role: str


def generate_admin_token(username: str) -> str:
    settings = get_settings()
    secret = (settings.admin_jwt_secret or "").strip()
    if not secret:
        raise AppError("Admin login is not configured", HTTP_SERVICE_UNAVAILABLE)

    expires_at = datetime.now(UTC) + ADMIN_TOKEN_EXPIRY
    claims: dict[str, Any] = {
        "sub": username,
        "role": "web_admin",
        "exp": expires_at,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def verify_admin_token(token: str) -> WebAdminTokenPayload:
    settings = get_settings()
    secret = (settings.admin_jwt_secret or "").strip()
    if not secret:
        raise AppError("Unauthorized", HTTP_UNAUTHORIZED)

    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AppError("Invalid or expired token", HTTP_UNAUTHORIZED) from exc

    role = payload.get("role")
    username = payload.get("sub")
    if role != "web_admin" or not username:
        raise AppError("Invalid token", HTTP_UNAUTHORIZED)

    return WebAdminTokenPayload(username=str(username), role=str(role))
