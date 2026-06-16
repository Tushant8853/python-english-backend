"""Progress stats derived from streak documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models.streak import STREAK_DAY_KEYS
from app.repositories.streak_repository import StreakRepository
from app.services.streak_service import get_week_start_monday_ymd, today_in_streak_zone


@dataclass(frozen=True)
class CurrentStreakReport:
    current_streak: int
    longest_streak: int
    streak_at_risk: bool
    last_completed_date: str | None
    today_completed: bool


def build_completed_dates_from_documents(documents: list) -> set[date]:
    completed: set[date] = set()
    for document in documents:
        try:
            monday = date.fromisoformat(document.week_start)
        except ValueError:
            continue
        for index, key in enumerate(STREAK_DAY_KEYS):
            if document.week_days.get(key):
                completed.add(monday + timedelta(days=index))
    return completed


def compute_longest_streak(completed: set[date]) -> int:
    if not completed:
        return 0
    sorted_dates = sorted(completed)
    best = 1
    run = 1
    for index in range(1, len(sorted_dates)):
        if sorted_dates[index] - sorted_dates[index - 1] == timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def compute_current_streak_report(
    completed: set[date],
    today: date | None = None,
) -> CurrentStreakReport:
    """
    Snapchat-style consecutive streak.

    - Counts backward from today if today is complete, else from yesterday if streak is still alive.
    - Resets to 0 when both today and yesterday are incomplete.
    - streakAtRisk: yesterday done but not today (user can still save streak today).
    """
    reference = today or today_in_streak_zone()
    yesterday = reference - timedelta(days=1)

    if not completed:
        return CurrentStreakReport(
            current_streak=0,
            longest_streak=0,
            streak_at_risk=False,
            last_completed_date=None,
            today_completed=False,
        )

    last_completed = max(completed)
    today_completed = reference in completed

    if reference in completed:
        start = reference
        streak_at_risk = False
    elif yesterday in completed:
        start = yesterday
        streak_at_risk = True
    else:
        return CurrentStreakReport(
            current_streak=0,
            longest_streak=compute_longest_streak(completed),
            streak_at_risk=False,
            last_completed_date=last_completed.isoformat(),
            today_completed=False,
        )

    count = 0
    cursor = start
    while cursor in completed:
        count += 1
        cursor -= timedelta(days=1)

    return CurrentStreakReport(
        current_streak=count,
        longest_streak=max(compute_longest_streak(completed), count),
        streak_at_risk=streak_at_risk,
        last_completed_date=last_completed.isoformat(),
        today_completed=today_completed,
    )


class ProgressReportService:
    def __init__(self, repository: StreakRepository | None = None) -> None:
        self._repository = repository or StreakRepository()

    async def _get_completed_dates(self, user_id: str) -> set[date]:
        documents = await self._repository.find_all_for_user(user_id)
        return build_completed_dates_from_documents(documents)

    async def get_current_streak_report(self, user_id: str) -> CurrentStreakReport:
        completed = await self._get_completed_dates(user_id)
        return compute_current_streak_report(completed)

    async def get_session_complete_total(self, user_id: str) -> int:
        documents = await self._repository.find_all_for_user(user_id)
        total = 0
        for document in documents:
            for key in STREAK_DAY_KEYS:
                if document.week_days.get(key):
                    total += 1
        return total

    async def get_consistency_percent_last_28_days(self, user_id: str) -> int:
        documents = await self._repository.find_all_for_user(user_id)
        by_week_start = {document.week_start: document for document in documents}
        today = today_in_streak_zone()
        completed = 0
        total = 28

        for offset in range(total):
            current = today - timedelta(days=offset)
            week_start = get_week_start_monday_ymd(current)
            document = by_week_start.get(week_start)
            if not document:
                continue
            day_key = STREAK_DAY_KEYS[current.weekday()]
            if document.week_days.get(day_key):
                completed += 1

        return min(100, round((completed / total) * 100))
