"""User document shape and FCM token helpers (mirrors Mongoose user.model.ts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

UserStatus = Literal["active", "deleted", "suspended"]
Platform = Literal["ios", "android"]


@dataclass
class FcmToken:
    token: str
    device_id: str
    platform: Platform
    updated_at: datetime

    def to_mongo(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "deviceId": self.device_id,
            "platform": self.platform,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> FcmToken:
        return cls(
            token=str(raw.get("token", "")),
            device_id=str(raw.get("deviceId", "")),
            platform=raw.get("platform", "android"),
            updated_at=_coerce_datetime(raw.get("updatedAt")),
        )


@dataclass
class IntakeAnswer:
    question_key: str
    value: str
    label: str = ""

    def to_mongo(self) -> dict[str, Any]:
        return {
            "questionKey": self.question_key,
            "value": self.value,
            "label": self.label,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> IntakeAnswer:
        return cls(
            question_key=str(raw.get("questionKey") or ""),
            value=str(raw.get("value") or ""),
            label=str(raw.get("label") or ""),
        )


@dataclass
class UserProfile:
    name: str = ""
    age: int | None = None
    best_describes_you: str = ""

    def to_mongo(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "age": self.age,
            "bestDescribesYou": self.best_describes_you,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> UserProfile | None:
        if not raw:
            return None
        return cls(
            name=str(raw.get("name", "")),
            age=raw.get("age"),
            best_describes_you=str(raw.get("bestDescribesYou", "")),
        )


@dataclass
class UserDocument:
    """In-memory representation of a MongoDB user document."""

    _id: ObjectId
    email: str
    firebase_uid: str
    status: UserStatus = "active"
    basic_onboarding_complete: bool = False
    intake_onboarding_complete: bool = False
    test_onboarding_complete: bool = False
    onboarding_complete: bool = False
    terms_accepted: bool = False
    terms_accepted_at: datetime | None = None
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None
    profile: UserProfile | None = None
    intake_answers: list[IntakeAnswer] = field(default_factory=list)
    placement_score: int | None = None
    placement_level: str = ""
    fcm_tokens: list[FcmToken] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> UserDocument:
        from app.utils.onboarding_progress import read_onboarding_flags_from_mongo

        basic, intake, test, complete = read_onboarding_flags_from_mongo(raw)
        intake_raw = raw.get("intakeAnswers") or []
        return cls(
            _id=raw["_id"],
            email=str(raw.get("email", "")),
            firebase_uid=str(raw.get("firebaseUid", "")),
            status=raw.get("status", "active"),
            basic_onboarding_complete=basic,
            intake_onboarding_complete=intake,
            test_onboarding_complete=test,
            onboarding_complete=complete,
            terms_accepted=bool(raw.get("termsAccepted", False)),
            terms_accepted_at=_coerce_optional_datetime(raw.get("termsAcceptedAt")),
            last_login_at=_coerce_optional_datetime(raw.get("lastLoginAt")),
            deleted_at=_coerce_optional_datetime(raw.get("deletedAt")),
            profile=UserProfile.from_mongo(raw.get("profile")),
            intake_answers=[
                IntakeAnswer.from_mongo(item) for item in intake_raw if isinstance(item, dict)
            ],
            placement_score=raw.get("placementScore"),
            placement_level=str(raw.get("placementLevel") or ""),
            fcm_tokens=[FcmToken.from_mongo(item) for item in raw.get("fcmTokens", [])],
            created_at=_coerce_optional_datetime(raw.get("createdAt")),
            updated_at=_coerce_optional_datetime(raw.get("updatedAt")),
        )

    def to_mongo(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "email": self.email.lower().strip(),
            "firebaseUid": self.firebase_uid.strip(),
            "status": self.status,
            "basicOnboardingComplete": self.basic_onboarding_complete,
            "intakeOnboardingComplete": self.intake_onboarding_complete,
            "testOnboardingComplete": self.test_onboarding_complete,
            "onboardingComplete": self.onboarding_complete,
            "termsAccepted": self.terms_accepted,
            "termsAcceptedAt": self.terms_accepted_at,
            "lastLoginAt": self.last_login_at,
            "deletedAt": self.deleted_at,
            "intakeAnswers": [answer.to_mongo() for answer in self.intake_answers],
            "placementScore": self.placement_score,
            "placementLevel": self.placement_level,
            "fcmTokens": [token.to_mongo() for token in self.fcm_tokens],
        }
        if self.profile is not None:
            payload["profile"] = self.profile.to_mongo()
        return payload


def upsert_fcm_token(
    user: UserDocument,
    token: str,
    device_id: str,
    platform: Platform,
) -> None:
    """Update or append an FCM token on the user document."""
    cleaned_token = token.strip()
    now = datetime.now(UTC)
    for index, existing in enumerate(user.fcm_tokens):
        if existing.token == cleaned_token:
            user.fcm_tokens[index] = FcmToken(
                token=cleaned_token,
                device_id=device_id.strip(),
                platform=platform,
                updated_at=now,
            )
            return
    user.fcm_tokens.append(
        FcmToken(
            token=cleaned_token,
            device_id=device_id.strip(),
            platform=platform,
            updated_at=now,
        )
    )


def remove_fcm_token(user: UserDocument, token: str) -> None:
    """Remove an FCM token from the user document."""
    cleaned_token = token.strip()
    user.fcm_tokens = [item for item in user.fcm_tokens if item.token != cleaned_token]


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _coerce_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return None
