"""Web admin CRUD for placement_questions catalog."""

from __future__ import annotations

import re

from bson import ObjectId
from bson.errors import InvalidId

from app.core.exceptions import AppError
from app.core.intake_question_types import SUPPORTED_LANGUAGES
from app.models.intake_question import IntakeOption
from app.models.placement_question import PlacementQuestionDocument, PlacementQuestionLocale
from app.repositories.placement_question_repository import PlacementQuestionRepository

QUESTION_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class PlacementQuestionAdminService:
    def __init__(self, repository: PlacementQuestionRepository | None = None) -> None:
        self._repository = repository or PlacementQuestionRepository()

    def _question_to_payload(self, question: PlacementQuestionDocument) -> dict[str, object]:
        content: dict[str, dict[str, object]] = {}
        for lang in SUPPORTED_LANGUAGES:
            block = question.content.get(lang, PlacementQuestionLocale())
            content[lang] = {
                "prompt": block.prompt,
                "options": [{"id": option.id, "label": option.label} for option in block.options],
            }
        return {
            "id": question.id,
            "questionKey": question.question_key,
            "order": question.order,
            "correctOptionId": question.correct_option_id,
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

    def _slug_from_prompt(self, prompt: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", prompt.strip().lower()).strip("_")
        if not slug:
            return ""
        if not slug[0].isalpha():
            slug = f"q_{slug}"
        return slug[:64]

    async def _allocate_question_key(self, content: dict[str, PlacementQuestionLocale], order: int) -> str:
        en_prompt = content.get("en", PlacementQuestionLocale()).prompt
        hi_prompt = content.get("hi", PlacementQuestionLocale()).prompt
        base = self._slug_from_prompt(en_prompt) or self._slug_from_prompt(hi_prompt) or f"placement_{order}"
        if not QUESTION_KEY_RE.match(base):
            base = f"placement_{order}"

        key = base
        suffix = 2
        while await self._repository.find_by_key(key):
            candidate = f"{base}_{suffix}"
            key = candidate[:64]
            suffix += 1
        return key

    def _parse_locale_block(self, raw: dict[str, object] | None) -> PlacementQuestionLocale:
        if not raw:
            return PlacementQuestionLocale()
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
        return PlacementQuestionLocale(
            prompt=str(raw.get("prompt") or "").strip(),
            options=options,
        )

    def _parse_content(self, raw: dict[str, object] | None) -> dict[str, PlacementQuestionLocale]:
        if not raw:
            return {lang: PlacementQuestionLocale() for lang in SUPPORTED_LANGUAGES}
        content: dict[str, PlacementQuestionLocale] = {}
        for lang in SUPPORTED_LANGUAGES:
            block = raw.get(lang)
            content[lang] = self._parse_locale_block(block if isinstance(block, dict) else None)
        return content

    def _validate_question(self, question: PlacementQuestionDocument) -> None:
        for lang in SUPPORTED_LANGUAGES:
            block = question.content.get(lang, PlacementQuestionLocale())
            if not block.prompt.strip():
                raise AppError(f"Prompt is required for {lang}", status_code=400)
            if len(block.options) < 2:
                raise AppError(f"At least two options required ({lang})", status_code=400)

        en_options = {option.id for option in question.content.get("en", PlacementQuestionLocale()).options}
        if question.correct_option_id not in en_options:
            raise AppError("correctOptionId must match an English option id", status_code=400)

    async def list_questions(self) -> dict[str, object]:
        questions = await self._repository.list_all(include_inactive=True)
        return {"items": [self._question_to_payload(question) for question in questions]}

    async def get_question(self, question_id: str) -> dict[str, object]:
        question = await self._repository.find_by_id(question_id)
        if question is None:
            raise AppError("Question not found", status_code=404)
        return self._question_to_payload(question)

    async def create_question(self, payload: dict[str, object]) -> dict[str, object]:
        order_raw = payload.get("order")
        if order_raw is None:
            order = (await self._repository.get_max_order()) + 1
        else:
            order = int(order_raw)

        content = self._parse_content(
            payload.get("content") if isinstance(payload.get("content"), dict) else None
        )
        question_key = await self._allocate_question_key(content, order)
        correct_option_id = str(payload.get("correctOptionId") or "").strip()

        question = PlacementQuestionDocument(
            question_key=question_key,
            order=order,
            correct_option_id=correct_option_id,
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

        if payload.get("order") is not None:
            existing.order = int(payload["order"])
        if payload.get("isActive") is not None:
            existing.is_active = bool(payload["isActive"])
        if payload.get("correctOptionId") is not None:
            existing.correct_option_id = str(payload["correctOptionId"]).strip()
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
