"""Firebase Admin ID token verification."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import Settings, get_settings
from app.core.constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_SERVER_ERROR
from app.core.exceptions import AppError

logger = logging.getLogger("english_guru.firebase")

_firebase_initialized = False


@dataclass(frozen=True)
class DecodedFirebaseUser:
    uid: str
    email: str


def _ensure_firebase_app(settings: Settings) -> None:
    global _firebase_initialized
    if _firebase_initialized:
        logger.debug("Firebase Admin already initialized")
        return

    logger.info(
        "Initializing Firebase Admin",
        extra={
            "meta": {
                "projectId": settings.firebase_project_id,
                "clientEmail": settings.firebase_client_email,
                "privateKeyPresent": bool(settings.firebase_private_key),
            }
        },
    )
    credential = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key": settings.firebase_private_key,
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    firebase_admin.initialize_app(credential)
    _firebase_initialized = True
    logger.info("Firebase Admin initialized successfully")


async def verify_firebase_id_token(id_token: str) -> DecodedFirebaseUser:
    """Verify a Firebase ID token and return uid and email."""
    settings = get_settings()
    _ensure_firebase_app(settings)

    logger.debug("Verifying Firebase ID token", extra={"meta": {"tokenLength": len(id_token)}})
    try:
        decoded = await asyncio.to_thread(auth.verify_id_token, id_token.strip())
    except Exception as exc:
        logger.warning("Firebase token verification failed", extra={"meta": {"error": str(exc)}})
        if isinstance(exc, AppError):
            raise
        raise AppError("Invalid Firebase ID token", HTTP_BAD_REQUEST) from exc

    email = decoded.get("email")
    if not email:
        raise AppError("Email not found in Firebase token", HTTP_BAD_REQUEST)

    logger.debug(
        "Firebase token verified",
        extra={"meta": {"uid": decoded.get("uid"), "email": email}},
    )
    return DecodedFirebaseUser(uid=str(decoded["uid"]), email=str(email))
