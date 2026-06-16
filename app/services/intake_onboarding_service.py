"""Dynamic intake questionnaire business logic."""

from __future__ import annotations

import json

from app.core.exceptions import AppError
from app.core.intake_question_types import INTAKE_QUESTION_TYPES, SUPPORTED_LANGUAGES
from app.models.intake_question import IntakeQuestionDocument, IntakeQuestionLocale
from app.models.user import IntakeAnswer, UserDocument
from app.repositories.intake_question_repository import IntakeQuestionRepository
from app.repositories.user_repository import UserRepository
from app.services.app_config_service import get_active_app_config
from app.utils.onboarding_progress import sync_onboarding_complete


class IntakeOnboardingService:
    def __init__(
        self,
        question_repository: IntakeQuestionRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._questions = question_repository or IntakeQuestionRepository()
        self._users = user_repository or UserRepository()

    async def _ensure_intake_enabled(self) -> None:
        config = await get_active_app_config()
        if not config.intake_onboarding.enabled:
            raise AppError("Intake onboarding is disabled", status_code=403)

    def _normalize_language(self, language: str | None) -> str:
        normalized = (language or "en").strip().lower()
        if normalized not in SUPPORTED_LANGUAGES:
            return "en"
        return normalized

    def _pick_locale(self, question: IntakeQuestionDocument, language: str) -> IntakeQuestionLocale:
        if language in question.content:
            return question.content[language]
        return question.content.get("en", IntakeQuestionLocale())

    def _question_to_client(
        self,
        question: IntakeQuestionDocument,
        language: str,
    ) -> dict[str, object]:
        locale = self._pick_locale(question, language)
        return {
            "questionKey": question.question_key,
            "type": question.question_type,
            "order": question.order,
            "required": question.required,
            "title": locale.title,
            "body": locale.body,
            "placeholder": locale.placeholder,
            "options": [{"id": option.id, "label": option.label} for option in locale.options],
            "minValue": locale.min_value,
            "maxValue": locale.max_value,
        }

    async def get_questions(self, language: str | None) -> dict[str, object]:
        await self._ensure_intake_enabled()
        lang = self._normalize_language(language)
        questions = await self._questions.list_active_questions()
        return {
            "language": lang,
            "questions": [self._question_to_client(question, lang) for question in questions],
        }

    def _validate_answer_value(
        self,
        question: IntakeQuestionDocument,
        language: str,
        raw_value: str | list[str],
    ) -> tuple[str, str]:
        locale = self._pick_locale(question, language)
        q_type = question.question_type

        if q_type not in INTAKE_QUESTION_TYPES:
            raise AppError(f"Unsupported question type: {q_type}", status_code=500)

        if q_type == "multiple_choice":
            if not isinstance(raw_value, list) or not raw_value:
                raise AppError(f"Answer required for {question.question_key}", status_code=400)
            option_ids = {option.id for option in locale.options}
            cleaned = [str(v).strip() for v in raw_value if str(v).strip()]
            if question.required and not cleaned:
                raise AppError(f"Answer required for {question.question_key}", status_code=400)
            for value in cleaned:
                if value not in option_ids:
                    raise AppError(f"Invalid option for {question.question_key}", status_code=400)
            labels = [
                next((opt.label for opt in locale.options if opt.id == value), value)
                for value in cleaned
            ]
            return json.dumps(cleaned), ", ".join(labels)

        value = str(raw_value).strip() if not isinstance(raw_value, list) else ""
        if question.required and not value:
            raise AppError(f"Answer required for {question.question_key}", status_code=400)

        if q_type in {"single_choice", "dropdown"}:
            option_ids = {option.id for option in locale.options}
            if value and value not in option_ids:
                raise AppError(f"Invalid option for {question.question_key}", status_code=400)
            label = next((opt.label for opt in locale.options if opt.id == value), value)
            return value, label

        if q_type == "yes_no":
            if value not in {"yes", "no"}:
                raise AppError(f"Answer must be yes or no for {question.question_key}", status_code=400)
            return value, "Yes" if value == "yes" else "No"

        if q_type == "number":
            try:
                parsed = float(value)
            except ValueError as exc:
                raise AppError(f"Valid number required for {question.question_key}", status_code=400) from exc
            if locale.min_value is not None and parsed < locale.min_value:
                raise AppError(f"Value too low for {question.question_key}", status_code=400)
            if locale.max_value is not None and parsed > locale.max_value:
                raise AppError(f"Value too high for {question.question_key}", status_code=400)
            return str(parsed), str(parsed)

        if q_type == "slider":
            try:
                parsed = int(float(value))
            except ValueError as exc:
                raise AppError(f"Valid slider value required for {question.question_key}", status_code=400) from exc
            min_v = locale.min_value if locale.min_value is not None else 1
            max_v = locale.max_value if locale.max_value is not None else 10
            if parsed < min_v or parsed > max_v:
                raise AppError(f"Slider value out of range for {question.question_key}", status_code=400)
            return str(parsed), str(parsed)

        if q_type == "rating":
            try:
                parsed = int(float(value))
            except ValueError as exc:
                raise AppError(f"Valid rating required for {question.question_key}", status_code=400) from exc
            max_v = locale.max_value if locale.max_value is not None else 5
            if parsed < 1 or parsed > max_v:
                raise AppError(f"Rating out of range for {question.question_key}", status_code=400)
            return str(parsed), str(parsed)

        if q_type == "date":
            if question.required and not value:
                raise AppError(f"Date required for {question.question_key}", status_code=400)
            return value, value

        # text and fallback
        return value, value

    def _user_stage_payload(self, user: UserDocument) -> dict[str, object]:
        profile = None
        if user.profile is not None:
            profile = {
                "name": user.profile.name,
                "age": user.profile.age,
                "bestDescribesYou": user.profile.best_describes_you,
            }
        return {
            "id": str(user._id),
            "profile": profile,
            "basicOnboardingComplete": user.basic_onboarding_complete,
            "intakeOnboardingComplete": user.intake_onboarding_complete,
            "testOnboardingComplete": user.test_onboarding_complete,
            "onboardingComplete": user.onboarding_complete,
        }

    async def submit_intake(
        self,
        user: UserDocument,
        answers: list[dict[str, object]],
        language: str | None = None,
    ) -> dict[str, object]:
        await self._ensure_intake_enabled()
        if not user.basic_onboarding_complete:
            raise AppError("Complete basic onboarding first", status_code=400)
        if user.intake_onboarding_complete:
            raise AppError("Intake onboarding already completed", status_code=400)

        lang = self._normalize_language(language)
        questions = await self._questions.list_active_questions()
        if not questions:
            raise AppError("Intake questions are not configured", status_code=503)

        answers_by_key: dict[str, str | list[str]] = {}
        for item in answers:
            key = str(item.get("questionKey") or "").strip()
            if not key:
                raise AppError("questionKey is required for each answer", status_code=400)
            if "value" not in item:
                raise AppError(f"value is required for {key}", status_code=400)
            answers_by_key[key] = item["value"]  # type: ignore[assignment]

        stored: list[IntakeAnswer] = []
        for question in questions:
            raw_value = answers_by_key.get(question.question_key)
            if raw_value is None:
                if question.required:
                    raise AppError(f"Missing answer for {question.question_key}", status_code=400)
                continue
            value, label = self._validate_answer_value(question, lang, raw_value)
            if not value and question.required:
                raise AppError(f"Answer required for {question.question_key}", status_code=400)
            if value:
                stored.append(
                    IntakeAnswer(
                        question_key=question.question_key,
                        value=value,
                        label=label,
                    )
                )

        user.intake_answers = stored
        user.intake_onboarding_complete = True
        sync_onboarding_complete(user)
        saved = await self._users.save_user(user)
        return {"user": self._user_stage_payload(saved)}
