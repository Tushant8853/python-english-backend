"""MongoDB access for lesson_library catalog."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_database
from app.models.lesson_library import LessonDocument


class LessonLibraryRepository:
    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection[dict[str, Any]] | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        if self._collection is None:
            self._collection = get_database()["lesson_library"]
        return self._collection

    async def find_by_id(self, lesson_id: str) -> LessonDocument | None:
        try:
            oid = ObjectId(lesson_id)
        except Exception:
            return None
        raw = await self.collection.find_one({"_id": oid})
        if not raw:
            return None
        return LessonDocument.from_mongo(raw)

    async def find_by_lesson_code(self, lesson_code: str) -> LessonDocument | None:
        code = lesson_code.strip().upper()
        if not code:
            return None
        raw = await self.collection.find_one({"lessonCode": code})
        if not raw:
            return None
        return LessonDocument.from_mongo(raw)

    async def find_by_day_number(self, day_number: int) -> LessonDocument | None:
        raw = await self.collection.find_one({"dayNumber": int(day_number)})
        if not raw:
            return None
        return LessonDocument.from_mongo(raw)

    async def list_lessons(
        self,
        *,
        level: str | None = None,
        topic: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LessonDocument], int]:
        query: dict[str, Any] = {}
        if level:
            query["level"] = level.strip().upper()
        if topic:
            query["topic"] = topic.strip().lower()
        if is_active is not None:
            query["isActive"] = bool(is_active)

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort([("sortOrder", 1), ("dayNumber", 1)])
            .skip(max(0, skip))
            .limit(min(max(1, limit), 200))
        )
        items = [LessonDocument.from_mongo(doc) async for doc in cursor]
        return items, int(total)

    async def insert(self, lesson: LessonDocument) -> LessonDocument:
        payload = lesson.to_mongo()
        result = await self.collection.insert_one(payload)
        raw = await self.collection.find_one({"_id": result.inserted_id})
        if not raw:
            raise RuntimeError("Failed to load lesson after insert")
        return LessonDocument.from_mongo(raw)

    async def save(self, lesson: LessonDocument) -> LessonDocument:
        if not lesson.id:
            return await self.insert(lesson)
        try:
            oid = ObjectId(lesson.id)
        except Exception as exc:
            raise ValueError("Invalid lesson id") from exc
        payload = lesson.to_mongo()
        await self.collection.update_one({"_id": oid}, {"$set": payload})
        raw = await self.collection.find_one({"_id": oid})
        if not raw:
            raise RuntimeError("Lesson not found after save")
        return LessonDocument.from_mongo(raw)

    async def delete_by_id(self, lesson_id: str) -> bool:
        try:
            oid = ObjectId(lesson_id)
        except Exception:
            return False
        result = await self.collection.delete_one({"_id": oid})
        return result.deleted_count > 0

    async def count_all(self) -> int:
        return int(await self.collection.count_documents({}))
