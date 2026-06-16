"""Seed default placement test questions when collection is empty."""

from __future__ import annotations

from app.models.intake_question import IntakeOption
from app.models.placement_question import PlacementQuestionDocument, PlacementQuestionLocale
from app.repositories.placement_question_repository import PlacementQuestionRepository


def _locale(
    en_prompt: str,
    hi_prompt: str,
    options: list[tuple[str, str, str]],
    *,
    correct_id: str,
) -> tuple[dict[str, PlacementQuestionLocale], str]:
    en_options = [IntakeOption(id=item[0], label=item[1]) for item in options]
    hi_options = [IntakeOption(id=item[0], label=item[2]) for item in options]
    return (
        {
            "en": PlacementQuestionLocale(prompt=en_prompt, options=en_options),
            "hi": PlacementQuestionLocale(prompt=hi_prompt, options=hi_options),
        },
        correct_id,
    )


def _build_default_questions() -> list[PlacementQuestionDocument]:
    seeds = [
        (
            "she_to_school",
            1,
            "She ___ to school every day.",
            "She ___ to school every day.",
            [("a", "goes", "goes"), ("b", "go", "go"), ("c", "going", "going"), ("d", "gone", "gone")],
            "a",
        ),
        (
            "opposite_happy",
            2,
            'What is the opposite of "happy"?',
            '"happy" का विपरीत शब्द क्या है?',
            [("a", "sad", "sad"), ("b", "angry", "angry"), ("c", "tired", "tired"), ("d", "hungry", "hungry")],
            "a",
        ),
        (
            "already_finished",
            3,
            "I have ___ finished my homework.",
            "I have ___ finished my homework.",
            [
                ("a", "already", "already"),
                ("b", "yet", "yet"),
                ("c", "since", "since"),
                ("d", "for", "for"),
            ],
            "a",
        ),
        (
            "past_eat",
            4,
            'What is the past tense of "eat"?',
            '"eat" का भूतकाल क्या है?',
            [("a", "ate", "ate"), ("b", "eaten", "eaten"), ("c", "eating", "eating"), ("d", "eats", "eats")],
            "a",
        ),
        (
            "correct_sentence",
            5,
            "Which sentence is correct?",
            "कौन सा वाक्य सही है?",
            [
                ("a", "He don't like coffee.", "He don't like coffee."),
                ("b", "He doesn't like coffee.", "He doesn't like coffee."),
                ("c", "He not like coffee.", "He not like coffee."),
                ("d", "He no like coffee.", "He no like coffee."),
            ],
            "b",
        ),
        (
            "similar_big",
            6,
            'Choose a word similar to "big".',
            '"big" जैसा शब्द चुनें।',
            [("a", "large", "large"), ("b", "small", "small"), ("c", "thin", "thin"), ("d", "short", "short")],
            "a",
        ),
        (
            "they_playing",
            7,
            "They ___ playing football now.",
            "They ___ playing football now.",
            [("a", "is", "is"), ("b", "am", "am"), ("c", "are", "are"), ("d", "be", "be")],
            "c",
        ),
        (
            "article_elephant",
            8,
            "I saw ___ elephant at the zoo.",
            "I saw ___ elephant at the zoo.",
            [("a", "a", "a"), ("b", "an", "an"), ("c", "the", "the"), ("d", "no article", "no article")],
            "b",
        ),
        (
            "if_rich",
            9,
            "If I ___ rich, I would travel the world.",
            "If I ___ rich, I would travel the world.",
            [("a", "am", "am"), ("b", "was", "was"), ("c", "were", "were"), ("d", "be", "be")],
            "c",
        ),
        (
            "taller_than",
            10,
            "She is ___ than her sister.",
            "She is ___ than her sister.",
            [
                ("a", "tall", "tall"),
                ("b", "taller", "taller"),
                ("c", "tallest", "tallest"),
                ("d", "more tall", "more tall"),
            ],
            "b",
        ),
    ]

    questions: list[PlacementQuestionDocument] = []
    for key, order, en_prompt, hi_prompt, options, correct_id in seeds:
        content, correct = _locale(en_prompt, hi_prompt, options, correct_id=correct_id)
        questions.append(
            PlacementQuestionDocument(
                question_key=key,
                order=order,
                correct_option_id=correct,
                is_active=True,
                content=content,
            )
        )
    return questions


async def ensure_default_placement_questions() -> None:
    repo = PlacementQuestionRepository()
    if await repo.count_active() > 0:
        return
    await repo.insert_many(_build_default_questions())
