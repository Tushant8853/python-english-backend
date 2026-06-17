"""Placement test question catalog (placement_questions collection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.intake_question import IntakeOption


@dataclass
class PlacementQuestionLocale:
    prompt: str = ""
    options: list[IntakeOption] = field(default_factory=list)

    def to_mongo(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "options": [option.to_mongo() for option in self.options],
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> PlacementQuestionLocale:
        if not raw:
            return cls()
        options_raw = raw.get("options") or []
        return cls(
            prompt=str(raw.get("prompt") or ""),
            options=[IntakeOption.from_mongo(item) for item in options_raw if isinstance(item, dict)],
        )


@dataclass
class PlacementQuestionDocument:
    question_key: str
    order: int
    correct_option_id: str | None = None
    is_active: bool = True
    content: dict[str, PlacementQuestionLocale] = field(default_factory=dict)
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        correct_id = (
            self.correct_option_id.strip().upper()
            if self.correct_option_id and self.correct_option_id.strip()
            else None
        )
        return {
            "questionKey": self.question_key.strip(),
            "order": int(self.order),
            "correctOptionId": correct_id,
            "isActive": bool(self.is_active),
            "content": {lang: block.to_mongo() for lang, block in self.content.items()},
            "updatedAt": now,
            "createdAt": self.created_at or now,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> PlacementQuestionDocument:
        content_raw = raw.get("content") or {}
        content = {
            str(lang): PlacementQuestionLocale.from_mongo(block if isinstance(block, dict) else None)
            for lang, block in content_raw.items()
            if isinstance(block, dict) or block is None
        }
        raw_correct = raw.get("correctOptionId")
        correct_option_id: str | None
        if raw_correct is None or str(raw_correct).strip() == "":
            correct_option_id = None
        else:
            correct_option_id = str(raw_correct).strip().upper()
        return cls(
            id=str(raw["_id"]),
            question_key=str(raw.get("questionKey") or ""),
            order=int(raw.get("order") or 0),
            correct_option_id=correct_option_id,
            is_active=bool(raw.get("isActive", True)),
            content=content,
            created_at=raw.get("createdAt"),
            updated_at=raw.get("updatedAt"),
        )
