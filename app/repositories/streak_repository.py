"""Streak persistence (collection: streaks)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.database.connection import get_database
from app.models.streak import STREAK_DAY_KEYS, StreakDocument, empty_week_days


class StreakRepository:
    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection[dict[str, Any]] | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        if self._collection is None:
            self._collection = get_database()["streaks"]
        return self._collection

    async def find_by_user_and_week(self, user_id: str, week_start: str) -> StreakDocument | None:
        if not ObjectId.is_valid(user_id):
            return None
        document = await self.collection.find_one(
            {"userId": ObjectId(user_id), "weekStart": week_start},
        )
        if not document:
            return None
        return StreakDocument.from_mongo(document)

    async def find_by_user_in_week_range(
        self,
        user_id: str,
        week_start_gte: str,
        week_start_lte: str,
    ) -> list[StreakDocument]:
        if not ObjectId.is_valid(user_id):
            return []
        cursor = self.collection.find(
            {
                "userId": ObjectId(user_id),
                "weekStart": {"$gte": week_start_gte, "$lte": week_start_lte},
            },
        )
        return [StreakDocument.from_mongo(doc) async for doc in cursor]

    async def find_all_for_user(self, user_id: str) -> list[StreakDocument]:
        if not ObjectId.is_valid(user_id):
            return []
        cursor = self.collection.find({"userId": ObjectId(user_id)})
        return [StreakDocument.from_mongo(doc) async for doc in cursor]

    async def upsert_week_day(
        self,
        user_id: str,
        week_start: str,
        month: str,
        day: str,
    ) -> StreakDocument:
        if not ObjectId.is_valid(user_id):
            raise ValueError("Invalid user id")
        if day not in STREAK_DAY_KEYS:
            raise ValueError("Invalid day")

        oid = ObjectId(user_id)
        filter_query = {"userId": oid, "weekStart": week_start}
        set_on_insert: dict[str, Any] = {
            "userId": oid,
            "weekStart": week_start,
            "month": month,
            "createdAt": datetime.now(UTC),
        }
        for key in STREAK_DAY_KEYS:
            if key != day:
                set_on_insert[f"weekDays.{key}"] = False

        update: dict[str, Any] = {
            "$set": {
                f"weekDays.{day}": True,
                "updatedAt": datetime.now(UTC),
            },
            "$setOnInsert": set_on_insert,
        }

        try:
            document = await self.collection.find_one_and_update(
                filter_query,
                update,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except Exception as exc:
            if getattr(exc, "code", None) != 11000:
                raise
            document = await self.collection.find_one_and_update(
                filter_query,
                {"$set": {f"weekDays.{day}": True, "updatedAt": datetime.now(UTC)}},
                return_document=ReturnDocument.AFTER,
            )

        if not document:
            raise RuntimeError("Streak document not found after update")
        return StreakDocument.from_mongo(document)

    def format_week_days(self, week_days: dict[str, bool] | None) -> dict[str, bool]:
        raw = week_days or empty_week_days()
        return {key: bool(raw.get(key)) for key in STREAK_DAY_KEYS}
