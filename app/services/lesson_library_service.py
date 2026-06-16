"""Lesson library business logic."""

from __future__ import annotations

from app.core.exceptions import AppError
from app.core.lesson_constants import LESSON_LEVELS, LESSON_TOPICS
from app.models.lesson_library import LessonDocument, QuizQuestion
from app.repositories.lesson_library_repository import LessonLibraryRepository
from app.utils.video_playback import playback_url_from_file_name


class LessonLibraryService:
    def __init__(self, repository: LessonLibraryRepository | None = None) -> None:
        self._repository = repository or LessonLibraryRepository()

    def _lesson_to_payload(self, lesson: LessonDocument) -> dict[str, object]:
        video_url = playback_url_from_file_name(lesson.video_file_name)
        if not video_url and lesson.external_video_url.strip():
            video_url = lesson.external_video_url.strip()
        return {
            "id": lesson.id,
            "lessonCode": lesson.lesson_code,
            "dayNumber": lesson.day_number,
            "title": lesson.title,
            "description": lesson.description,
            "level": lesson.level,
            "topic": lesson.topic,
            "videoFileName": lesson.video_file_name,
            "externalVideoUrl": lesson.external_video_url,
            "videoUrl": video_url,
            "quiz": [
                {
                    "question": q.question,
                    "options": q.options,
                    "correctIndex": q.correct_index,
                }
                for q in lesson.quiz
            ],
            "isActive": lesson.is_active,
            "sortOrder": lesson.sort_order,
            "createdAt": lesson.created_at.isoformat() if lesson.created_at else None,
            "updatedAt": lesson.updated_at.isoformat() if lesson.updated_at else None,
        }

    def _validate_level(self, level: str) -> str:
        normalized = level.strip().upper()
        if normalized not in LESSON_LEVELS:
            raise AppError(
                f"Invalid level. Allowed: {', '.join(LESSON_LEVELS)}",
                status_code=400,
            )
        return normalized

    def _validate_topic(self, topic: str) -> str:
        normalized = topic.strip().lower()
        if normalized not in LESSON_TOPICS:
            raise AppError(
                f"Invalid topic. Allowed: {', '.join(LESSON_TOPICS)}",
                status_code=400,
            )
        return normalized

    def _parse_quiz(self, quiz_raw: list[dict[str, object]] | None) -> list[QuizQuestion]:
        if not quiz_raw:
            return []
        questions: list[QuizQuestion] = []
        for item in quiz_raw:
            question = str(item.get("question") or "").strip()
            options_raw = item.get("options") or []
            if not isinstance(options_raw, list):
                raise AppError("Quiz options must be a list", status_code=400)
            options = [str(o).strip() for o in options_raw if str(o).strip()]
            if not question:
                raise AppError("Quiz question text is required", status_code=400)
            if len(options) < 2:
                raise AppError("Each quiz question needs at least 2 options", status_code=400)
            correct_index = int(item.get("correctIndex", 0))
            if correct_index < 0 or correct_index >= len(options):
                raise AppError("Quiz correctIndex is out of range", status_code=400)
            questions.append(
                QuizQuestion(
                    question=question,
                    options=options,
                    correct_index=correct_index,
                )
            )
        return questions

    async def list_lessons(
        self,
        *,
        level: str | None = None,
        topic: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        skip = (page - 1) * page_size
        if level:
            self._validate_level(level)
        if topic:
            self._validate_topic(topic)

        items, total = await self._repository.list_lessons(
            level=level,
            topic=topic,
            is_active=is_active,
            skip=skip,
            limit=page_size,
        )
        return {
            "items": [self._lesson_to_payload(lesson) for lesson in items],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        }

    async def get_lesson(self, lesson_id: str) -> dict[str, object]:
        lesson = await self._repository.find_by_id(lesson_id)
        if not lesson:
            raise AppError("Lesson not found", status_code=404)
        return self._lesson_to_payload(lesson)

    async def create_lesson(self, payload: dict[str, object]) -> dict[str, object]:
        lesson_code = str(payload.get("lessonCode") or "").strip().upper()
        title = str(payload.get("title") or "").strip()
        if not lesson_code:
            raise AppError("lessonCode is required", status_code=400)
        if not title:
            raise AppError("title is required", status_code=400)

        existing = await self._repository.find_by_lesson_code(lesson_code)
        if existing:
            raise AppError("lessonCode already exists", status_code=409)

        day_number = int(payload.get("dayNumber") or 0)
        if day_number < 1:
            raise AppError("dayNumber must be at least 1", status_code=400)
        day_existing = await self._repository.find_by_day_number(day_number)
        if day_existing:
            raise AppError("dayNumber already exists", status_code=409)

        quiz_raw = payload.get("quiz")
        quiz_list = self._parse_quiz(quiz_raw if isinstance(quiz_raw, list) else [])

        lesson = LessonDocument(
            lesson_code=lesson_code,
            day_number=day_number,
            title=title,
            description=str(payload.get("description") or "").strip(),
            level=self._validate_level(str(payload.get("level") or "A1")),
            topic=self._validate_topic(str(payload.get("topic") or "grammar")),
            video_file_name=str(payload.get("videoFileName") or "").strip(),
            external_video_url=str(payload.get("externalVideoUrl") or "").strip(),
            quiz=quiz_list,
            is_active=bool(payload.get("isActive", True)),
            sort_order=int(payload.get("sortOrder") or day_number),
        )
        saved = await self._repository.insert(lesson)
        return self._lesson_to_payload(saved)

    async def update_lesson(self, lesson_id: str, payload: dict[str, object]) -> dict[str, object]:
        lesson = await self._repository.find_by_id(lesson_id)
        if not lesson:
            raise AppError("Lesson not found", status_code=404)

        if "lessonCode" in payload and payload["lessonCode"] is not None:
            new_code = str(payload["lessonCode"]).strip().upper()
            if new_code and new_code != lesson.lesson_code:
                existing = await self._repository.find_by_lesson_code(new_code)
                if existing and existing.id != lesson.id:
                    raise AppError("lessonCode already exists", status_code=409)
                lesson.lesson_code = new_code

        if "dayNumber" in payload and payload["dayNumber"] is not None:
            new_day = int(payload["dayNumber"])
            if new_day < 1:
                raise AppError("dayNumber must be at least 1", status_code=400)
            if new_day != lesson.day_number:
                day_existing = await self._repository.find_by_day_number(new_day)
                if day_existing and day_existing.id != lesson.id:
                    raise AppError("dayNumber already exists", status_code=409)
                lesson.day_number = new_day

        if "title" in payload and payload["title"] is not None:
            title = str(payload["title"]).strip()
            if not title:
                raise AppError("title cannot be empty", status_code=400)
            lesson.title = title

        if "description" in payload and payload["description"] is not None:
            lesson.description = str(payload["description"]).strip()

        if "level" in payload and payload["level"] is not None:
            lesson.level = self._validate_level(str(payload["level"]))

        if "topic" in payload and payload["topic"] is not None:
            lesson.topic = self._validate_topic(str(payload["topic"]))

        if "videoFileName" in payload and payload["videoFileName"] is not None:
            lesson.video_file_name = str(payload["videoFileName"]).strip()

        if "externalVideoUrl" in payload and payload["externalVideoUrl"] is not None:
            lesson.external_video_url = str(payload["externalVideoUrl"]).strip()

        if "quiz" in payload and payload["quiz"] is not None:
            quiz_raw = payload["quiz"]
            lesson.quiz = self._parse_quiz(quiz_raw if isinstance(quiz_raw, list) else [])

        if "isActive" in payload and payload["isActive"] is not None:
            lesson.is_active = bool(payload["isActive"])

        if "sortOrder" in payload and payload["sortOrder"] is not None:
            lesson.sort_order = int(payload["sortOrder"])

        saved = await self._repository.save(lesson)
        return self._lesson_to_payload(saved)

    async def delete_lesson(self, lesson_id: str) -> None:
        deleted = await self._repository.delete_by_id(lesson_id)
        if not deleted:
            raise AppError("Lesson not found", status_code=404)

    async def set_lesson_video_file_name(self, lesson_id: str, file_name: str) -> dict[str, object]:
        lesson = await self._repository.find_by_id(lesson_id)
        if not lesson:
            raise AppError("Lesson not found", status_code=404)
        lesson.video_file_name = file_name.strip()
        lesson.external_video_url = ""
        saved = await self._repository.save(lesson)
        return self._lesson_to_payload(saved)
