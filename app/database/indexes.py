"""MongoDB index setup for user lifecycle (Wellness-style soft delete + re-register)."""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_database

logger = logging.getLogger("english_guru.database")

# Legacy Mongoose / early schema — blocks re-login after soft-delete (same email, new doc).
_LEGACY_GLOBAL_EMAIL_UNIQUE_NAMES = frozenset({"email_unique", "email_1"})
_LEGACY_GLOBAL_FIREBASE_UID_UNIQUE_NAMES = frozenset({"firebaseUid_unique", "firebaseUid_1"})


async def _drop_legacy_global_unique_indexes(collection: AsyncIOMotorCollection) -> None:
    """Remove global unique email/firebaseUid indexes (deleted rows block re-register)."""
    info = await collection.index_information()
    for name, spec in info.items():
        if name == "_id_":
            continue
        keys = list(spec.get("key", []))
        is_global_unique = bool(spec.get("unique")) and not spec.get("partialFilterExpression")
        if not is_global_unique:
            continue
        if len(keys) != 1:
            continue
        field = keys[0][0]
        if field not in {"email", "firebaseUid"}:
            continue
        await collection.drop_index(name)
        logger.warning(
            "Dropped legacy global unique user index",
            extra={"meta": {"indexName": name, "field": field}},
        )

    # Named legacy indexes (Mongoose) even if shape check missed them.
    info = await collection.index_information()
    for legacy_name in _LEGACY_GLOBAL_EMAIL_UNIQUE_NAMES | _LEGACY_GLOBAL_FIREBASE_UID_UNIQUE_NAMES:
        if legacy_name in info:
            await collection.drop_index(legacy_name)
            logger.warning(
                "Dropped legacy user index by name",
                extra={"meta": {"indexName": legacy_name}},
            )


async def ensure_user_indexes() -> None:
    """
    Ensure indexes support multiple deleted rows per email/firebaseUid while keeping
    at most one active user per email and per firebaseUid (partial unique indexes).
    """
    collection = get_database()["users"]

    await _drop_legacy_global_unique_indexes(collection)

    await collection.create_index(
        [("email", 1), ("firebaseUid", 1), ("status", 1)],
        name="email_firebaseUid_status",
    )
    await collection.create_index(
        [("firebaseUid", 1), ("status", 1)],
        name="firebaseUid_status",
    )
    await collection.create_index(
        [("email", 1), ("status", 1)],
        name="email_status",
    )
    await collection.create_index(
        [("firebaseUid", 1)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="firebaseUid_active_unique",
    )
    await collection.create_index(
        [("email", 1)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="email_active_unique",
    )
    # Keep startup index maintenance out of normal INFO logs.
    logger.debug("User indexes ensured")


async def ensure_streak_indexes() -> None:
    """Unique (userId, weekStart) for weekly streak documents."""
    collection = get_database()["streaks"]
    await collection.create_index(
        [("userId", 1), ("weekStart", 1)],
        unique=True,
        name="userId_weekStart_unique",
    )
    logger.debug("Streak indexes ensured")


async def ensure_lesson_library_indexes() -> None:
    """Unique lessonCode and dayNumber for catalog lessons."""
    collection = get_database()["lesson_library"]
    await collection.create_index(
        [("lessonCode", 1)],
        unique=True,
        name="lessonCode_unique",
    )
    await collection.create_index(
        [("dayNumber", 1)],
        unique=True,
        name="dayNumber_unique",
    )
    await collection.create_index(
        [("level", 1), ("sortOrder", 1)],
        name="level_sortOrder",
    )
    await collection.create_index(
        [("isActive", 1), ("sortOrder", 1)],
        name="isActive_sortOrder",
    )
    logger.debug("Lesson library indexes ensured")


async def ensure_intake_question_indexes() -> None:
    """Unique questionKey and order lookup for intake_questions."""
    collection = get_database()["intake_questions"]
    await collection.create_index(
        [("questionKey", 1)],
        unique=True,
        name="questionKey_unique",
    )
    await collection.create_index(
        [("isActive", 1), ("order", 1)],
        name="isActive_order",
    )
    logger.debug("Intake question indexes ensured")


async def ensure_placement_question_indexes() -> None:
    """Unique questionKey and order lookup for placement_questions."""
    collection = get_database()["placement_questions"]
    await collection.create_index(
        [("questionKey", 1)],
        unique=True,
        name="questionKey_unique",
    )
    await collection.create_index(
        [("isActive", 1), ("order", 1)],
        name="isActive_order",
    )
    logger.debug("Placement question indexes ensured")
