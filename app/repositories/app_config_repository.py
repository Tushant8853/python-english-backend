"""App configuration persistence (collection: appconfigs)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_database
from app.models.app_config import AppConfigDocument, default_app_config_payload


class AppConfigRepository:
    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection[dict[str, Any]] | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        if self._collection is None:
            self._collection = get_database()["appconfigs"]
        return self._collection

    async def find_active(self) -> AppConfigDocument | None:
        document = await self.collection.find_one({"isActive": True})
        if not document:
            return None
        return AppConfigDocument.from_mongo(document)

    async def ensure_active(self) -> AppConfigDocument:
        existing = await self.find_active()
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        payload = default_app_config_payload()
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return AppConfigDocument.from_mongo(payload)

    async def save(self, config: AppConfigDocument) -> AppConfigDocument:
        now = datetime.now(UTC)
        update_payload = config.to_mongo()
        update_payload["updatedAt"] = now
        await self.collection.update_one(
            {"_id": config._id},
            {"$set": update_payload},
        )
        document = await self.collection.find_one({"_id": config._id})
        if not document:
            raise RuntimeError("App config missing after save")
        return AppConfigDocument.from_mongo(document)
