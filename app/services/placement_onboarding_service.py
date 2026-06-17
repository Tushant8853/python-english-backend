"""Mobile placement test business logic."""

from __future__ import annotations

from app.core.exceptions import AppError
from app.core.intake_question_types import SUPPORTED_LANGUAGES
from app.models.placement_question import PlacementQuestionDocument, PlacementQuestionLocale
from app.models.user import UserDocument
from app.repositories.placement_question_repository import PlacementQuestionRepository
from app.repositories.user_repository import UserRepository
from app.utils.onboarding_progress import sync_onboarding_complete
from app.utils.placement_score import calculate_placement_score, level_from_score


class PlacementOnboardingService:
    def __init__(
        self,
        question_repository: PlacementQuestionRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._questions = question_repository or PlacementQuestionRepository()
        self._users = user_repository or UserRepository()

    def _normalize_language(self, language: str | None) -> str:
        normalized = (language or "en").strip().lower()
        if normalized not in SUPPORTED_LANGUAGES:
            return "en"
        return normalized

    def _pick_locale(self, question: PlacementQuestionDocument, language: str) -> PlacementQuestionLocale:
        if language in question.content:
            return question.content[language]
        return question.content.get("en", PlacementQuestionLocale())

    def _question_to_client(
        self,
        question: PlacementQuestionDocument,
        language: str,
    ) -> dict[str, object]:
        locale = self._pick_locale(question, language)
        return {
            "questionKey": question.question_key,
            "order": question.order,
            "prompt": locale.prompt,
            "options": [{"id": option.id, "label": option.label} for option in locale.options],
        }

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
            "placementScore": user.placement_score,
            "placementLevel": user.placement_level,
        }

    async def get_questions(self, language: str | None) -> dict[str, object]:
        lang = self._normalize_language(language)
        questions = await self._questions.list_active_questions()
        return {
            "language": lang,
            "questions": [self._question_to_client(question, lang) for question in questions],
        }

    async def complete_placement(
        self,
        user: UserDocument,
        answers: list[dict[str, object]],
    ) -> dict[str, object]:
        if not user.basic_onboarding_complete:
            raise AppError("Complete basic onboarding first", status_code=400)
        if not user.intake_onboarding_complete:
            raise AppError("Complete intake onboarding first", status_code=400)

        questions = await self._questions.list_active_questions()
        if not questions:
            raise AppError("No placement questions are configured", status_code=400)

        answers_by_key: dict[str, str] = {}
        for item in answers:
            key = str(item.get("questionKey") or "").strip()
            option_id = str(item.get("optionId") or "").strip()
            if not key or not option_id:
                raise AppError("questionKey and optionId are required for each answer", status_code=400)
            answers_by_key[key] = option_id

        correct_count = 0
        scorable_questions = [
            question
            for question in questions
            if question.correct_option_id and question.correct_option_id.strip()
        ]
        for question in questions:
            selected = answers_by_key.get(question.question_key)
            if not selected:
                raise AppError(f"Missing answer for {question.question_key}", status_code=400)
            locale = self._pick_locale(question, "en")
            valid_ids = {option.id for option in locale.options}
            if selected not in valid_ids:
                raise AppError(f"Invalid option for {question.question_key}", status_code=400)

        for question in scorable_questions:
            selected = answers_by_key[question.question_key]
            if selected == question.correct_option_id:
                correct_count += 1

        total = len(scorable_questions)
        score = calculate_placement_score(correct_count, total)
        level = level_from_score(score)

        user.placement_score = score
        user.placement_level = level
        user.test_onboarding_complete = True
        sync_onboarding_complete(user)
        saved = await self._users.save_user(user)

        return {
            "user": self._user_stage_payload(saved),
            "score": score,
            "level": level,
            "correctCount": correct_count,
            "totalQuestions": total,
        }
