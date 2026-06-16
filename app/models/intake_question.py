"""Dynamic intake question catalog (intake_questions collection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class IntakeOption:
    id: str
    label: str

    def to_mongo(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label}

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> IntakeOption:
        return cls(id=str(raw.get("id") or ""), label=str(raw.get("label") or ""))


@dataclass
class IntakeQuestionLocale:
    title: str = ""
    body: str = ""
    placeholder: str = ""
    options: list[IntakeOption] = field(default_factory=list)
    min_value: int | None = None
    max_value: int | None = None

    def to_mongo(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": self.title,
            "body": self.body,
            "placeholder": self.placeholder,
            "options": [option.to_mongo() for option in self.options],
        }
        if self.min_value is not None:
            payload["minValue"] = self.min_value
        if self.max_value is not None:
            payload["maxValue"] = self.max_value
        return payload

    @classmethod
    def from_mongo(cls, raw: dict[str, Any] | None) -> IntakeQuestionLocale:
        if not raw:
            return cls()
        options_raw = raw.get("options") or []
        return cls(
            title=str(raw.get("title") or ""),
            body=str(raw.get("body") or ""),
            placeholder=str(raw.get("placeholder") or ""),
            options=[IntakeOption.from_mongo(item) for item in options_raw if isinstance(item, dict)],
            min_value=raw.get("minValue"),
            max_value=raw.get("maxValue"),
        )


@dataclass
class IntakeQuestionDocument:
    question_key: str
    question_type: str
    order: int
    required: bool = True
    is_active: bool = True
    content: dict[str, IntakeQuestionLocale] = field(default_factory=dict)
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        return {
            "questionKey": self.question_key.strip(),
            "type": self.question_type.strip(),
            "order": int(self.order),
            "required": bool(self.required),
            "isActive": bool(self.is_active),
            "content": {lang: block.to_mongo() for lang, block in self.content.items()},
            "updatedAt": now,
            "createdAt": self.created_at or now,
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> IntakeQuestionDocument:
        content_raw = raw.get("content") or {}
        content = {
            str(lang): IntakeQuestionLocale.from_mongo(block if isinstance(block, dict) else None)
            for lang, block in content_raw.items()
            if isinstance(block, dict) or block is None
        }
        return cls(
            id=str(raw["_id"]),
            question_key=str(raw.get("questionKey") or ""),
            question_type=str(raw.get("type") or ""),
            order=int(raw.get("order") or 0),
            required=bool(raw.get("required", True)),
            is_active=bool(raw.get("isActive", True)),
            content=content,
            created_at=raw.get("createdAt"),
            updated_at=raw.get("updatedAt"),
        )
