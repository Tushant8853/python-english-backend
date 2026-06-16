#!/usr/bin/env python3
"""
Strip legacy "Day N: " prefixes from lesson_library titles (seed v1 artifact).

Usage (from python-backend/):
  python scripts/fix_lesson_titles.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import close_database, connect_database
from app.repositories.lesson_library_repository import LessonLibraryRepository

_DAY_TITLE_PREFIX = re.compile(r"^Day\s+\d+:\s*", re.IGNORECASE)
_DAY_QUIZ_PREFIX = re.compile(r"^Day\s+\d+\s*[—–-]\s*", re.IGNORECASE)


async def run() -> int:
    if not await connect_database():
        print("FAIL: Could not connect to MongoDB")
        return 1

    repo = LessonLibraryRepository()
    items, total = await repo.list_lessons(limit=200)
    updated = 0

    for lesson in items:
        new_title = _DAY_TITLE_PREFIX.sub("", lesson.title).strip()
        changed = new_title != lesson.title

        new_quiz = []
        for q in lesson.quiz:
            cleaned_q = _DAY_QUIZ_PREFIX.sub("", q.question).strip()
            if cleaned_q != q.question:
                changed = True
            new_quiz.append(
                type(q)(
                    question=cleaned_q,
                    options=q.options,
                    correct_index=q.correct_index,
                )
            )

        if not changed:
            continue

        lesson.title = new_title or lesson.title
        lesson.quiz = new_quiz
        if "60-day learning path" in lesson.description.lower():
            lesson.description = lesson.description.replace(
                " Part of the English Guru 60-day learning path.",
                "",
            )
            changed = True

        await repo.save(lesson)
        updated += 1

    print(f"PASS: Updated {updated} of {total} lessons (removed Day N from titles).")
    await close_database()
    return 0


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
