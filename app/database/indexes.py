"""MongoDB index setup for user lifecycle (Wellness-style soft delete + re-register)."""

from __future__ import annotations

import logging

from app.database.connection import get_database

logger = logging.getLogger("english_guru.database")


async def ensure_user_indexes() -> None:
    """
    Ensure indexes support multiple deleted rows per firebaseUid while keeping
    at most one active user per firebaseUid (partial unique index).
    """
    collection = get_database()["users"]

    await collection.create_index(
        [("email", 1), ("firebaseUid", 1), ("status", 1)],
        name="email_firebaseUid_status",
    )
    await collection.create_index(
        [("firebaseUid", 1), ("status", 1)],
        name="firebaseUid_status",
    )
    await collection.create_index(
        [("firebaseUid", 1)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="firebaseUid_active_unique",
    )
    logger.info("User indexes ensured")
