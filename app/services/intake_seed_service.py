"""Seed default dynamic intake questions when collection is empty."""

from __future__ import annotations

from app.models.intake_question import IntakeOption, IntakeQuestionDocument, IntakeQuestionLocale
from app.repositories.intake_question_repository import IntakeQuestionRepository


def _build_default_questions() -> list[IntakeQuestionDocument]:
    def locale(
        en_title: str,
        hi_title: str,
        *,
        en_body: str = "",
        hi_body: str = "",
        options: list[tuple[str, str, str, str]] | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> dict[str, IntakeQuestionLocale]:
        en_options = (
            [IntakeOption(id=item[0], label=item[1]) for item in options] if options else []
        )
        hi_options = (
            [IntakeOption(id=item[0], label=item[3]) for item in options] if options else []
        )
        return {
            "en": IntakeQuestionLocale(
                title=en_title,
                body=en_body,
                options=en_options,
                min_value=min_value,
                max_value=max_value,
            ),
            "hi": IntakeQuestionLocale(
                title=hi_title,
                body=hi_body,
                options=hi_options,
                min_value=min_value,
                max_value=max_value,
            ),
        }

    return [
        IntakeQuestionDocument(
            question_key="learning_goal",
            question_type="single_choice",
            order=1,
            content=locale(
                "Why are you learning English?",
                "आप अंग्रेज़ी क्यों सीख रहे हैं?",
                options=[
                    ("job", "Job / career", "job", "नौकरी / करियर"),
                    ("study", "Study abroad", "study", "विदेश में पढ़ाई"),
                    ("travel", "Travel", "travel", "यात्रा"),
                    ("speaking", "Speaking confidence", "speaking", "बोलने का आत्मविश्वास"),
                ],
            ),
        ),
        IntakeQuestionDocument(
            question_key="daily_time",
            question_type="single_choice",
            order=2,
            content=locale(
                "How much time can you study each day?",
                "आप रोज़ कितना समय पढ़ सकते हैं?",
                options=[
                    ("15", "15 minutes", "15", "15 मिनट"),
                    ("30", "30 minutes", "30", "30 मिनट"),
                    ("45", "45 minutes", "45", "45 मिनट"),
                    ("60", "60+ minutes", "60", "60+ मिनट"),
                ],
            ),
        ),
        IntakeQuestionDocument(
            question_key="confidence_level",
            question_type="single_choice",
            order=3,
            content=locale(
                "How confident do you feel speaking English?",
                "अंग्रेज़ी बोलने में आप कितने आत्मविश्वासी हैं?",
                options=[
                    ("low", "Not confident", "low", "ज़्यादा आत्मविश्वास नहीं"),
                    ("medium", "Somewhat confident", "medium", "कुछ हद तक आत्मविश्वासी"),
                    ("high", "Very confident", "high", "बहुत आत्मविश्वासी"),
                ],
            ),
        ),
        IntakeQuestionDocument(
            question_key="study_reminder",
            question_type="yes_no",
            order=4,
            content=locale(
                "Would you like daily study reminders?",
                "क्या आप रोज़ाना पढ़ाई की याद दिलाना चाहेंगे?",
            ),
        ),
        IntakeQuestionDocument(
            question_key="motivation_rating",
            question_type="rating",
            order=5,
            content=locale(
                "How motivated are you to improve your English?",
                "अंग्रेज़ी सुधारने के लिए आप कितने प्रेरित हैं?",
                min_value=1,
                max_value=5,
            ),
        ),
    ]


async def ensure_default_intake_questions() -> None:
    repo = IntakeQuestionRepository()
    if await repo.count_active() > 0:
        return
    await repo.insert_many(_build_default_questions())
