"""JWT access token issue and verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR
from app.core.exceptions import AppError

ALGORITHM = "HS256"


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: str
    token_type: str


def generate_access_token(user_id: str) -> str:
    """Issue a signed JWT compatible with the Node jsonwebtoken payload."""
    settings = get_settings()
    secret = settings.jwt_secret.strip()
    if not secret:
        raise AppError("JWT_SECRET is not configured", HTTP_INTERNAL_SERVER_ERROR)

    expires_at = datetime.now(UTC) + settings.jwt_expiry_delta
    claims: dict[str, Any] = {
        "userId": user_id,
        "type": "access",
        "exp": expires_at,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def verify_access_token(token: str) -> AccessTokenPayload:
    """Decode and validate a bearer access token."""
    settings = get_settings()
    secret = settings.jwt_secret.strip()
    if not secret:
        raise AppError("JWT secret is not configured", HTTP_INTERNAL_SERVER_ERROR)

    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AppError("Invalid or expired token", HTTP_BAD_REQUEST) from exc

    user_id = payload.get("userId")
    token_type = payload.get("type")
    if not user_id or token_type != "access":
        raise AppError("Invalid access token", HTTP_BAD_REQUEST)

    return AccessTokenPayload(user_id=str(user_id), token_type=str(token_type))
