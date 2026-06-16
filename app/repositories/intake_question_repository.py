"""MongoDB access for intake_questions catalog."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_database
from app.models.intake_question import IntakeQuestionDocument


class IntakeQuestionRepository:
    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection[dict[str, Any]] | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        if self._collection is None:
            self._collection = get_database()["intake_questions"]
        return self._collection

    async def list_active_questions(self) -> list[IntakeQuestionDocument]:
        cursor = self.collection.find({"isActive": True}).sort([("order", 1), ("questionKey", 1)])
        return [IntakeQuestionDocument.from_mongo(doc) async for doc in cursor]

    async def count_active(self) -> int:
        return int(await self.collection.count_documents({"isActive": True}))

    async def insert_many(self, questions: list[IntakeQuestionDocument]) -> int:
        if not questions:
            return 0
        payloads = [question.to_mongo() for question in questions]
        result = await self.collection.insert_many(payloads)
        return len(result.inserted_ids)

    async def list_all(self, *, include_inactive: bool = True) -> list[IntakeQuestionDocument]:
        query: dict[str, object] = {} if include_inactive else {"isActive": True}
        cursor = self.collection.find(query).sort([("order", 1), ("questionKey", 1)])
        return [IntakeQuestionDocument.from_mongo(doc) async for doc in cursor]

    async def find_by_id(self, question_id: str) -> IntakeQuestionDocument | None:
        try:
            oid = ObjectId(question_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": oid})
        return IntakeQuestionDocument.from_mongo(doc) if doc else None

    async def find_by_key(self, question_key: str) -> IntakeQuestionDocument | None:
        doc = await self.collection.find_one({"questionKey": question_key.strip()})
        return IntakeQuestionDocument.from_mongo(doc) if doc else None

    async def get_max_order(self) -> int:
        doc = await self.collection.find_one(sort=[("order", -1)])
        if not doc:
            return 0
        return int(doc.get("order") or 0)

    async def create(self, question: IntakeQuestionDocument) -> IntakeQuestionDocument:
        payload = question.to_mongo()
        result = await self.collection.insert_one(payload)
        saved = await self.collection.find_one({"_id": result.inserted_id})
        if not saved:
            raise RuntimeError("Failed to load created intake question")
        return IntakeQuestionDocument.from_mongo(saved)

    async def replace(self, question: IntakeQuestionDocument) -> IntakeQuestionDocument:
        if not question.id:
            raise ValueError("question id is required")
        oid = ObjectId(question.id)
        existing = await self.collection.find_one({"_id": oid})
        payload = question.to_mongo()
        if existing and existing.get("createdAt"):
            payload["createdAt"] = existing["createdAt"]
        await self.collection.replace_one({"_id": oid}, payload)
        saved = await self.collection.find_one({"_id": oid})
        if not saved:
            raise RuntimeError("Failed to load updated intake question")
        return IntakeQuestionDocument.from_mongo(saved)

    async def delete(self, question_id: str) -> bool:
        try:
            oid = ObjectId(question_id)
        except Exception:
            return False
        result = await self.collection.delete_one({"_id": oid})
        return result.deleted_count > 0

    async def reorder(self, ordered_ids: list[str]) -> list[IntakeQuestionDocument]:
        for index, question_id in enumerate(ordered_ids, start=1):
            try:
                oid = ObjectId(question_id)
            except Exception as exc:
                raise ValueError(f"Invalid question id: {question_id}") from exc
            await self.collection.update_one(
                {"_id": oid},
                {"$set": {"order": index}},
            )
        return await self.list_all(include_inactive=True)
