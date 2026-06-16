"""Weekly streak document (Mon–Sun completion flags per user per week)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bson import ObjectId

STREAK_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DATE_KEY_RE = r"^\d{4}-\d{2}-\d{2}$"
MONTH_KEY_RE = r"^\d{4}-\d{2}$"


def empty_week_days() -> dict[str, bool]:
    return {key: False for key in STREAK_DAY_KEYS}


@dataclass
class StreakDocument:
    user_id: str
    week_start: str
    month: str
    week_days: dict[str, bool]

    def to_mongo(self) -> dict[str, Any]:
        return {
            "userId": ObjectId(self.user_id),
            "weekStart": self.week_start,
            "month": self.month,
            "weekDays": {key: bool(self.week_days.get(key)) for key in STREAK_DAY_KEYS},
        }

    @classmethod
    def from_mongo(cls, raw: dict[str, Any]) -> StreakDocument:
        week_days_raw = raw.get("weekDays") or {}
        return cls(
            user_id=str(raw.get("userId", "")),
            week_start=str(raw.get("weekStart", "")),
            month=str(raw.get("month", "")),
            week_days={key: bool(week_days_raw.get(key)) for key in STREAK_DAY_KEYS},
        )
