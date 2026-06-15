"""App configuration document (Wellness-style appconfigs collection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId


@dataclass
class PaywallConfig:
    enabled: bool = False
    closable: bool = False

    def to_mongo(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "closable": self.closable if self.enabled else False}

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> PaywallConfig:
        if not raw:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            closable=bool(raw.get("closable", False)),
        )


@dataclass
class IntroVideoConfig:
    enabled: bool = True
    show_every_launch: bool = False
    video_file_name: str = ""

    def to_mongo(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "showEveryLaunch": self.show_every_launch,
            "videoFileName": self.video_file_name,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> IntroVideoConfig:
        if not raw:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", True)),
            show_every_launch=bool(raw.get("showEveryLaunch", False)),
            video_file_name=str(raw.get("videoFileName", "")),
        )


@dataclass
class SalesVideoConfig:
    enabled: bool = False
    video_file_name: str = ""

    def to_mongo(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "videoFileName": self.video_file_name,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> SalesVideoConfig:
        if not raw:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            video_file_name=str(raw.get("videoFileName", "")),
        )


@dataclass
class ForceUpdateConfig:
    enabled: bool = False
    minimum_version: str = "1.0.0"
    title: str = "Update required"
    message: str = "Please update the app to continue."
    android_store_url: str = ""
    ios_store_url: str = ""

    def to_mongo(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "minimumVersion": self.minimum_version,
            "title": self.title,
            "message": self.message,
            "androidStoreUrl": self.android_store_url,
            "iosStoreUrl": self.ios_store_url,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> ForceUpdateConfig:
        if not raw:
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            minimum_version=str(raw.get("minimumVersion", "1.0.0")),
            title=str(raw.get("title", "Update required")),
            message=str(raw.get("message", "Please update the app to continue.")),
            android_store_url=str(raw.get("androidStoreUrl", "")),
            ios_store_url=str(raw.get("iosStoreUrl", "")),
        )


@dataclass
class ChatUiConfig:
    show_call: bool = False
    show_voice: bool = False
    show_mic: bool = False
    show_delete_user: bool = True

    def to_mongo(self) -> dict[str, Any]:
        return {
            "showCall": self.show_call,
            "showVoice": self.show_voice,
            "showMic": self.show_mic,
            "showDeleteUser": self.show_delete_user,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> ChatUiConfig:
        if not raw:
            return cls()
        return cls(
            show_call=bool(raw.get("showCall", False)),
            show_voice=bool(raw.get("showVoice", False)),
            show_mic=bool(raw.get("showMic", False)),
            show_delete_user=bool(raw.get("showDeleteUser", True)),
        )


@dataclass
class AppConfigDocument:
    _id: ObjectId
    is_active: bool = True
    paywall: PaywallConfig = field(default_factory=PaywallConfig)
    intro_video: IntroVideoConfig = field(default_factory=IntroVideoConfig)
    sales_video: SalesVideoConfig = field(default_factory=SalesVideoConfig)
    force_update: ForceUpdateConfig = field(default_factory=ForceUpdateConfig)
    chat_ui: ChatUiConfig = field(default_factory=ChatUiConfig)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> AppConfigDocument:
        return cls(
            _id=raw["_id"],
            is_active=bool(raw.get("isActive", True)),
            paywall=PaywallConfig.from_mongo(raw.get("paywall")),
            intro_video=IntroVideoConfig.from_mongo(raw.get("introVideo")),
            sales_video=SalesVideoConfig.from_mongo(raw.get("salesVideo")),
            force_update=ForceUpdateConfig.from_mongo(raw.get("forceUpdate")),
            chat_ui=ChatUiConfig.from_mongo(raw.get("chatUi")),
            created_at=_coerce_datetime(raw.get("createdAt")),
            updated_at=_coerce_datetime(raw.get("updatedAt")),
        )

    def to_mongo(self) -> dict[str, Any]:
        paywall = self.paywall.to_mongo()
        if not paywall["enabled"]:
            paywall["closable"] = False
        return {
            "isActive": self.is_active,
            "paywall": paywall,
            "introVideo": self.intro_video.to_mongo(),
            "salesVideo": self.sales_video.to_mongo(),
            "forceUpdate": self.force_update.to_mongo(),
            "chatUi": self.chat_ui.to_mongo(),
        }


def default_app_config_payload() -> dict[str, Any]:
    now = datetime.now(UTC)
    doc = AppConfigDocument(
        _id=ObjectId(),
        created_at=now,
        updated_at=now,
    )
    payload = doc.to_mongo()
    payload["createdAt"] = now
    payload["updatedAt"] = now
    return payload


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return None
