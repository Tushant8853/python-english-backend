"""User persistence against the shared MongoDB users collection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_database
from app.models.user import UserDocument, UserProfile


class UserRepository:
    """Async repository for user documents (collection: users)."""

    def __init__(self) -> None:
        self._collection: AsyncIOMotorCollection[dict[str, Any]] | None = None

    @property
    def collection(self) -> AsyncIOMotorCollection[dict[str, Any]]:
        if self._collection is None:
            self._collection = get_database()["users"]
        return self._collection

    async def find_active_by_firebase_uid(self, firebase_uid: str) -> UserDocument | None:
        document = await self.collection.find_one({"firebaseUid": firebase_uid, "status": "active"})
        if not document:
            return None
        return UserDocument.from_mongo(document)

    async def find_by_firebase_uid(self, firebase_uid: str) -> UserDocument | None:
        document = await self.collection.find_one({"firebaseUid": firebase_uid.strip()})
        if not document:
            return None
        return UserDocument.from_mongo(document)

    async def find_active_by_id(self, user_id: str) -> UserDocument | None:
        if not ObjectId.is_valid(user_id):
            return None
        document = await self.collection.find_one({"_id": ObjectId(user_id), "status": "active"})
        if not document:
            return None
        return UserDocument.from_mongo(document)

    async def create_user(
        self,
        *,
        email: str,
        firebase_uid: str,
        terms_accepted: bool,
    ) -> UserDocument:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "email": email.lower().strip(),
            "firebaseUid": firebase_uid.strip(),
            "status": "active",
            "onboardingComplete": False,
            "termsAccepted": terms_accepted,
            "termsAcceptedAt": now if terms_accepted else None,
            "lastLoginAt": now,
            "fcmTokens": [],
            "createdAt": now,
            "updatedAt": now,
        }
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return UserDocument.from_mongo(payload)

    async def save_user(self, user: UserDocument) -> UserDocument:
        now = datetime.now(UTC)
        user.updated_at = now
        update_payload = user.to_mongo()
        update_payload["updatedAt"] = now
        await self.collection.update_one(
            {"_id": user._id},
            {"$set": update_payload},
        )
        document = await self.collection.find_one({"_id": user._id})
        if not document:
            raise RuntimeError("User document missing after save")
        return UserDocument.from_mongo(document)

    async def soft_delete_user(self, user: UserDocument) -> UserDocument:
        now = datetime.now(UTC)
        user.status = "deleted"
        user.fcm_tokens = []
        user.updated_at = now
        await self.collection.update_one(
            {"_id": user._id},
            {
                "$set": {
                    "status": "deleted",
                    "fcmTokens": [],
                    "updatedAt": now,
                }
            },
        )
        document = await self.collection.find_one({"_id": user._id})
        if not document:
            raise RuntimeError("User document missing after soft delete")
        return UserDocument.from_mongo(document)

    async def complete_onboarding(
        self,
        user: UserDocument,
        *,
        profile: UserProfile,
    ) -> UserDocument:
        user.profile = profile
        user.onboarding_complete = True
        saved = await self.save_user(user)
        await self.collection.update_one(
            {"_id": user._id},
            {"$unset": {"name": "", "age": "", "bestDescribesYou": ""}},
        )
        return saved
