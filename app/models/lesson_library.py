"""Lesson catalog document model (lesson_library collection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId


@dataclass
class QuizQuestion:
    question: str
    options: list[str]
    correct_index: int

    def to_mongo(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "options": list(self.options),
            "correctIndex": int(self.correct_index),
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> QuizQuestion:
        return cls(
            question=str(raw.get("question") or ""),
            options=[str(o) for o in (raw.get("options") or [])],
            correct_index=int(raw.get("correctIndex", 0)),
        )


@dataclass
class LessonDocument:
    lesson_code: str
    day_number: int
    title: str
    description: str
    level: str
    topic: str
    video_file_name: str = ""
    external_video_url: str = ""
    quiz: list[QuizQuestion] = field(default_factory=list)
    is_active: bool = True
    sort_order: int = 0
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "lessonCode": self.lesson_code.strip().upper(),
            "dayNumber": int(self.day_number),
            "title": self.title.strip(),
            "description": self.description.strip(),
            "level": self.level.strip().upper(),
            "topic": self.topic.strip().lower(),
            "videoFileName": self.video_file_name.strip(),
            "externalVideoUrl": self.external_video_url.strip(),
            "quiz": [q.to_mongo() for q in self.quiz],
            "isActive": bool(self.is_active),
            "sortOrder": int(self.sort_order),
            "updatedAt": now,
        }
        if self.created_at is None:
            payload["createdAt"] = now
        else:
            payload["createdAt"] = self.created_at
        return payload

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> LessonDocument:
        quiz_raw = raw.get("quiz") or []
        return cls(
            id=str(raw["_id"]),
            lesson_code=str(raw.get("lessonCode") or ""),
            day_number=int(raw.get("dayNumber") or 0),
            title=str(raw.get("title") or ""),
            description=str(raw.get("description") or ""),
            level=str(raw.get("level") or ""),
            topic=str(raw.get("topic") or ""),
            video_file_name=str(raw.get("videoFileName") or ""),
            external_video_url=str(raw.get("externalVideoUrl") or ""),
            quiz=[QuizQuestion.from_mongo(q) for q in quiz_raw if isinstance(q, dict)],
            is_active=bool(raw.get("isActive", True)),
            sort_order=int(raw.get("sortOrder") or 0),
            created_at=raw.get("createdAt"),
            updated_at=raw.get("updatedAt"),
        )
