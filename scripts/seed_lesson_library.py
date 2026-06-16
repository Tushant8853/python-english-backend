#!/usr/bin/env python3
"""
Seed lesson_library with 100 MVP lessons (video URLs + quizzes).

Usage (from python-backend/):
  python scripts/seed_lesson_library.py
  python scripts/seed_lesson_library.py --force   # drop existing and re-seed
  python scripts/seed_lesson_library.py --count 10  # seed fewer for testing

Requires MONGODB_URI in .env or environment.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.lesson_constants import LESSON_LEVELS, LESSON_TOPICS
from app.database.connection import close_database, connect_database
from app.database.indexes import ensure_lesson_library_indexes
from app.models.lesson_library import LessonDocument, QuizQuestion
from app.repositories.lesson_library_repository import LessonLibraryRepository

# Public sample MP4s (replace with your S3/CDN URLs in production via admin dashboard).
SAMPLE_VIDEOS = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4",
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
]

LESSON_TITLES: dict[str, list[str]] = {
    "grammar": [
        "Present Simple Basics",
        "Articles A and An",
        "Plural Nouns",
        "This, That, These, Those",
        "Question Words",
        "Past Simple Introduction",
        "Future with Will",
        "Comparatives",
        "Superlatives",
        "Prepositions of Place",
        "Prepositions of Time",
        "Countable and Uncountable",
        "Modal Can and Could",
        "Present Continuous",
        "Past Continuous",
        "Present Perfect Intro",
        "Passive Voice Basics",
        "Conditional Type 1",
        "Reported Speech Intro",
        "Relative Clauses",
    ],
    "vocabulary": [
        "Family Members",
        "Colors and Shapes",
        "Food and Drinks",
        "Days and Months",
        "Weather Words",
        "Clothing Vocabulary",
        "Jobs and Professions",
        "House and Furniture",
        "Transportation",
        "Body Parts",
        "Health and Illness",
        "Shopping Phrases",
        "Travel Essentials",
        "Office Vocabulary",
        "Technology Terms",
        "Nature and Animals",
        "Hobbies and Sports",
        "Emotions and Feelings",
        "City Places",
        "Cooking Verbs",
    ],
    "listening": [
        "Greetings in Context",
        "Ordering at a Café",
        "Asking for Directions",
        "Phone Conversations",
        "Airport Announcements",
        "Shopping Dialogues",
        "Doctor Appointments",
        "Hotel Check-in",
        "Job Interview Basics",
        "Weather Reports",
        "News Headlines Slow",
        "Podcast Introduction",
        "Meeting Small Talk",
        "Public Transport Info",
        "Restaurant Recommendations",
        "Travel Plans Discussion",
        "Describing Your Day",
        "Making Appointments",
        "Complaints and Solutions",
        "Social Invitations",
    ],
    "reading": [
        "My Daily Routine",
        "A Letter to a Friend",
        "Signs and Notices",
        "Short Story: The Park",
        "Email Etiquette",
        "Recipe Instructions",
        "Travel Blog Post",
        "Product Reviews",
        "News Article Skim",
        "Job Advertisement",
        "School Notice Board",
        "Biography Snippet",
        "Opinion Paragraph",
        "Instructions Manual",
        "Festival Celebration",
        "City Guide Excerpt",
        "Health Tips Article",
        "Interview Transcript",
        "Science for Kids",
        "Book Summary",
    ],
    "conversation": [
        "Introducing Yourself",
        "Talking About Hobbies",
        "Making Plans",
        "Giving Opinions",
        "Agreeing and Disagreeing",
        "Describing People",
        "Talking About the Past",
        "Future Goals",
        "Problem Solving",
        "Apologizing Politely",
        "Giving Advice",
        "Asking for Help",
        "Celebrating Success",
        "Handling Misunderstandings",
        "Networking Introduction",
        "Presentation Openers",
        "Negotiation Basics",
        "Cultural Differences",
        "Formal vs Informal",
        "Closing Conversations",
    ],
}

QUIZ_BANK: dict[str, list[tuple[str, list[str], int]]] = {
    "grammar": [
        ("Choose the correct sentence.", ["She go to school.", "She goes to school.", "She going school.", "She goed school."], 1),
        ("Which is past tense of 'eat'?", ["eated", "ate", "eaten", "eating"], 1),
        ("Select the correct article: ___ apple.", ["a", "an", "the", "no article"], 1),
    ],
    "vocabulary": [
        ("What is the opposite of 'hot'?", ["warm", "cold", "wet", "dry"], 1),
        ("Which word means 'very tired'?", ["exhausted", "excited", "hungry", "brave"], 0),
        ("'Physician' is similar to ___", ["teacher", "doctor", "driver", "chef"], 1),
    ],
    "listening": [
        ("When someone says 'Could you repeat that?', they want you to ___", ["speak louder", "say it again", "write it down", "translate"], 1),
        ("In a café, 'To go' means ___", ["eat here", "take away", "pay later", "free refill"], 1),
        ("'Boarding now' at an airport means ___", ["land", "get on the plane", "check bags", "leave city"], 1),
    ],
    "reading": [
        ("The main idea of a paragraph is usually in the ___", ["last line only", "topic sentence", "middle word", "title only"], 1),
        ("To skim means to read ___", ["every word slowly", "quickly for gist", "aloud", "backwards"], 1),
        ("In an email, 'Regards' is a ___", ["greeting", "closing", "subject", "attachment"], 1),
    ],
    "conversation": [
        ("A polite way to disagree: ___", ["You're wrong!", "I see your point, but...", "No way!", "Stop talking"], 1),
        ("'How have you been?' asks about ___", ["your height", "recent life", "your job only", "weather"], 1),
        ("To invite someone: ___", ["Go away.", "Would you like to join us?", "I don't care.", "Maybe never."], 1),
    ],
}


def level_for_day(day: int) -> str:
    if day <= 20:
        return "A1"
    if day <= 40:
        return "A2"
    if day <= 60:
        return "B1"
    if day <= 80:
        return "B2"
    return "C1"


def topic_for_day(day: int) -> str:
    return LESSON_TOPICS[(day - 1) % len(LESSON_TOPICS)]


def title_for(day: int, topic: str) -> str:
    titles = LESSON_TITLES[topic]
    return titles[(day - 1) % len(titles)]


def build_quiz(topic: str, day: int) -> list[QuizQuestion]:
    bank = QUIZ_BANK[topic]
    questions: list[QuizQuestion] = []
    for offset in range(3):
        q_text, options, correct = bank[(day + offset) % len(bank)]
        questions.append(
            QuizQuestion(
                question=q_text,
                options=options,
                correct_index=correct,
            )
        )
    return questions


def build_lesson(catalog_index: int) -> LessonDocument:
    topic = topic_for_day(catalog_index)
    level = level_for_day(catalog_index)
    title = title_for(catalog_index, topic)
    video_url = SAMPLE_VIDEOS[(catalog_index - 1) % len(SAMPLE_VIDEOS)]
    return LessonDocument(
        lesson_code=f"L{catalog_index:03d}",
        day_number=catalog_index,
        title=title,
        description=(
            f"{level} {topic} lesson. Practice {title.lower()} with video, "
            f"examples, and a short quiz."
        ),
        level=level,
        topic=topic,
        external_video_url=video_url,
        quiz=build_quiz(topic, catalog_index),
        is_active=True,
        sort_order=catalog_index,
    )


async def run(force: bool, count: int) -> int:
    if not await connect_database():
        print("FAIL: Could not connect to MongoDB. Set MONGODB_URI in .env")
        return 1

    await ensure_lesson_library_indexes()
    repo = LessonLibraryRepository()

    existing = await repo.count_all()
    if existing > 0 and not force:
        print(f"SKIP: lesson_library already has {existing} documents. Use --force to re-seed.")
        await close_database()
        return 0

    if force and existing > 0:
        await repo.collection.delete_many({})
        print(f"Cleared {existing} existing lessons.")

    count = max(1, min(count, 100))
    inserted = 0
    for day in range(1, count + 1):
        lesson = build_lesson(day)
        await repo.insert(lesson)
        inserted += 1
        if day % 20 == 0 or day == count:
            print(f"  inserted {day}/{count}...")

    print(f"PASS: Seeded {inserted} lessons into lesson_library.")
    await close_database()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed lesson_library collection")
    parser.add_argument("--force", action="store_true", help="Delete existing lessons and re-seed")
    parser.add_argument("--count", type=int, default=100, help="Number of lessons (1-100, default 100)")
    args = parser.parse_args()
    code = asyncio.run(run(force=args.force, count=args.count))
    sys.exit(code)


if __name__ == "__main__":
    main()
