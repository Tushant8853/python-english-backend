"""Web admin CRUD for intake_questions catalog."""

from __future__ import annotations

import re

from bson import ObjectId
from bson.errors import InvalidId

from app.core.exceptions import AppError
from app.core.intake_question_types import INTAKE_QUESTION_TYPES, SUPPORTED_LANGUAGES
from app.models.intake_question import IntakeOption, IntakeQuestionDocument, IntakeQuestionLocale
from app.repositories.intake_question_repository import IntakeQuestionRepository

QUESTION_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
CHOICE_TYPES = {"single_choice", "multiple_choice", "dropdown"}
RANGE_TYPES = {"slider", "rating", "number"}


class IntakeQuestionAdminService:
    def __init__(self, repository: IntakeQuestionRepository | None = None) -> None:
        self._repository = repository or IntakeQuestionRepository()

    def _question_to_payload(self, question: IntakeQuestionDocument) -> dict[str, object]:
        content: dict[str, dict[str, object]] = {}
        for lang in SUPPORTED_LANGUAGES:
            block = question.content.get(lang, IntakeQuestionLocale())
            content[lang] = {
                "title": block.title,
                "body": block.body,
                "placeholder": block.placeholder,
                "options": [{"id": option.id, "label": option.label} for option in block.options],
                "minValue": block.min_value,
                "maxValue": block.max_value,
            }
        return {
            "id": question.id,
            "questionKey": question.question_key,
            "type": question.question_type,
            "order": question.order,
            "required": question.required,
            "isActive": question.is_active,
            "content": content,
            "createdAt": question.created_at.isoformat() if question.created_at else None,
            "updatedAt": question.updated_at.isoformat() if question.updated_at else None,
        }

    def _parse_object_id(self, question_id: str) -> ObjectId:
        try:
            return ObjectId(question_id)
        except (InvalidId, TypeError) as exc:
            raise AppError("Invalid question id", status_code=400) from exc

    def _slug_from_title(self, title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")
        if not slug:
            return ""
        if not slug[0].isalpha():
            slug = f"q_{slug}"
        return slug[:64]

    async def _allocate_question_key(
        self,
        content: dict[str, IntakeQuestionLocale],
        order: int,
    ) -> str:
        en_title = content.get("en", IntakeQuestionLocale()).title
        hi_title = content.get("hi", IntakeQuestionLocale()).title
        base = self._slug_from_title(en_title) or self._slug_from_title(hi_title) or f"question_{order}"
        if not QUESTION_KEY_RE.match(base):
            base = f"question_{order}"

        key = base
        suffix = 2
        while await self._repository.find_by_key(key):
            candidate = f"{base}_{suffix}"
            key = candidate[:64]
            suffix += 1
        return key

    def _parse_locale_block(self, raw: dict[str, object] | None) -> IntakeQuestionLocale:
        if not raw:
            return IntakeQuestionLocale()
        options_raw = raw.get("options") or []
        options: list[IntakeOption] = []
        if isinstance(options_raw, list):
            for item in options_raw:
                if not isinstance(item, dict):
                    continue
                option_id = str(item.get("id") or "").strip()
                label = str(item.get("label") or "").strip()
                if option_id and label:
                    options.append(IntakeOption(id=option_id, label=label))
        min_value = raw.get("minValue")
        max_value = raw.get("maxValue")
        return IntakeQuestionLocale(
            title=str(raw.get("title") or "").strip(),
            body=str(raw.get("body") or "").strip(),
            placeholder=str(raw.get("placeholder") or "").strip(),
            options=options,
            min_value=int(min_value) if min_value is not None else None,
            max_value=int(max_value) if max_value is not None else None,
        )

    def _parse_content(self, raw: dict[str, object] | None) -> dict[str, IntakeQuestionLocale]:
        if not raw:
            return {lang: IntakeQuestionLocale() for lang in SUPPORTED_LANGUAGES}
        content: dict[str, IntakeQuestionLocale] = {}
        for lang in SUPPORTED_LANGUAGES:
            block = raw.get(lang)
            content[lang] = self._parse_locale_block(block if isinstance(block, dict) else None)
        return content

    def _validate_question(self, question: IntakeQuestionDocument) -> None:
        q_type = question.question_type
        if q_type not in INTAKE_QUESTION_TYPES:
            raise AppError(
                f"Invalid type. Allowed: {', '.join(INTAKE_QUESTION_TYPES)}",
                status_code=400,
            )

        for lang in SUPPORTED_LANGUAGES:
            block = question.content.get(lang, IntakeQuestionLocale())
            if not block.title.strip():
                raise AppError(f"Title is required for {lang}", status_code=400)
            if q_type in CHOICE_TYPES:
                if len(block.options) < 2:
                    raise AppError(
                        f"At least two options required for {q_type} ({lang})",
                        status_code=400,
                    )
            if q_type == "rating":
                max_v = block.max_value if block.max_value is not None else 5
                if max_v < 1:
                    raise AppError("rating maxValue must be at least 1", status_code=400)
            if q_type == "slider":
                min_v = block.min_value if block.min_value is not None else 1
                max_v = block.max_value if block.max_value is not None else 10
                if min_v >= max_v:
                    raise AppError("slider minValue must be less than maxValue", status_code=400)

    async def list_questions(self) -> dict[str, object]:
        questions = await self._repository.list_all(include_inactive=True)
        return {"items": [self._question_to_payload(question) for question in questions]}

    async def get_question(self, question_id: str) -> dict[str, object]:
        question = await self._repository.find_by_id(question_id)
        if question is None:
            raise AppError("Question not found", status_code=404)
        return self._question_to_payload(question)

    async def create_question(self, payload: dict[str, object]) -> dict[str, object]:
        q_type = str(payload.get("type") or "single_choice").strip()
        order_raw = payload.get("order")
        if order_raw is None:
            order = (await self._repository.get_max_order()) + 1
        else:
            order = int(order_raw)

        content = self._parse_content(
            payload.get("content") if isinstance(payload.get("content"), dict) else None
        )
        question_key = await self._allocate_question_key(content, order)

        question = IntakeQuestionDocument(
            question_key=question_key,
            question_type=q_type,
            order=order,
            required=bool(payload.get("required", True)),
            is_active=bool(payload.get("isActive", True)),
            content=content,
        )
        self._validate_question(question)
        saved = await self._repository.create(question)
        return self._question_to_payload(saved)

    async def update_question(self, question_id: str, payload: dict[str, object]) -> dict[str, object]:
        existing = await self._repository.find_by_id(question_id)
        if existing is None:
            raise AppError("Question not found", status_code=404)

        if payload.get("type") is not None:
            existing.question_type = str(payload["type"]).strip()
        if payload.get("order") is not None:
            existing.order = int(payload["order"])
        if payload.get("required") is not None:
            existing.required = bool(payload["required"])
        if payload.get("isActive") is not None:
            existing.is_active = bool(payload["isActive"])
        if payload.get("content") is not None and isinstance(payload["content"], dict):
            existing.content = self._parse_content(payload["content"])

        self._validate_question(existing)
        saved = await self._repository.replace(existing)
        return self._question_to_payload(saved)

    async def delete_question(self, question_id: str) -> None:
        deleted = await self._repository.delete(question_id)
        if not deleted:
            raise AppError("Question not found", status_code=404)

    async def reorder_questions(self, ordered_ids: list[str]) -> dict[str, object]:
        if not ordered_ids:
            raise AppError("orderedIds is required", status_code=400)
        try:
            questions = await self._repository.reorder(ordered_ids)
        except ValueError as exc:
            raise AppError(str(exc), status_code=400) from exc
        return {"items": [self._question_to_payload(question) for question in questions]}
