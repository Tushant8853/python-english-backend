"""Placement test scoring helpers."""

from __future__ import annotations

from typing import Literal

PlacementLevelId = Literal[
    "beginner",
    "elementary",
    "intermediate",
    "upperIntermediate",
    "advanced",
]


def level_from_score(score: int) -> PlacementLevelId:
    if score >= 90:
        return "advanced"
    if score >= 75:
        return "upperIntermediate"
    if score >= 60:
        return "intermediate"
    if score >= 40:
        return "elementary"
    return "beginner"


def calculate_placement_score(correct_count: int, total_questions: int) -> int:
    if total_questions <= 0:
        return 0
    return round((correct_count / total_questions) * 100)
