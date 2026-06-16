"""Weekly streak business logic (Asia/Kolkata week boundaries by default)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.streak import STREAK_DAY_KEYS
from app.repositories.streak_repository import StreakRepository

DATE_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _streak_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().streak_timezone)


def today_in_streak_zone() -> date:
    return datetime.now(_streak_timezone()).date()


def _today_in_zone() -> date:
    return today_in_streak_zone()


def get_week_start_monday_ymd(value: date | None = None) -> str:
    """Monday of the calendar week containing `value` in the streak timezone."""
    current = value or _today_in_zone()
    monday = current - timedelta(days=current.weekday())
    return monday.isoformat()


def get_month_ym(value: date | None = None) -> str:
    current = value or _today_in_zone()
    return f"{current.year:04d}-{current.month:02d}"


def day_key_from_date_key(date_key: str) -> str | None:
    if not DATE_KEY_PATTERN.match(date_key.strip()):
        return None
    try:
        parsed = date.fromisoformat(date_key.strip())
    except ValueError:
        return None
    return STREAK_DAY_KEYS[parsed.weekday()]


def week_start_from_date_key(date_key: str) -> str | None:
    if not DATE_KEY_PATTERN.match(date_key.strip()):
        return None
    try:
        parsed = date.fromisoformat(date_key.strip())
    except ValueError:
        return None
    monday = parsed - timedelta(days=parsed.weekday())
    return monday.isoformat()


class StreakService:
    def __init__(self, repository: StreakRepository | None = None) -> None:
        self._repository = repository or StreakRepository()

    async def get_current_week_status(self, user_id: str) -> dict[str, object]:
        week_start = get_week_start_monday_ymd()
        document = await self._repository.find_by_user_and_week(user_id, week_start)
        week_days = self._repository.format_week_days(document.week_days if document else None)
        return {"weekStart": week_start, "weekDays": week_days}

    async def update_streak_day(self, user_id: str, day: str) -> dict[str, object]:
        normalized = day.strip().lower()
        if normalized not in STREAK_DAY_KEYS:
            raise AppError("Invalid day", status_code=400)
        now = _today_in_zone()
        week_start = get_week_start_monday_ymd(now)
        month = get_month_ym(now)
        document = await self._repository.upsert_week_day(user_id, week_start, month, normalized)
        return self._format_streak_document(document)

    async def update_streak_for_date_key(self, user_id: str, date_key: str) -> dict[str, object]:
        day = day_key_from_date_key(date_key)
        week_start = week_start_from_date_key(date_key)
        if not day or not week_start:
            raise AppError("Invalid date", status_code=400)
        try:
            parsed = date.fromisoformat(date_key.strip())
        except ValueError as exc:
            raise AppError("Invalid date", status_code=400) from exc
        month = f"{parsed.year:04d}-{parsed.month:02d}"
        document = await self._repository.upsert_week_day(user_id, week_start, month, day)
        return self._format_streak_document(document)

    async def check_in_today(self, user_id: str, date_key: str | None = None) -> dict[str, object]:
        """Mark a calendar day complete (daily lesson check-in). Idempotent."""
        key = (date_key or _today_in_zone().isoformat()).strip()
        day = day_key_from_date_key(key)
        week_start = week_start_from_date_key(key)
        was_complete = False
        if day and week_start:
            document = await self._repository.find_by_user_and_week(user_id, week_start)
            if document:
                was_complete = bool(document.week_days.get(day))
        result = await self.update_streak_for_date_key(user_id, key)
        return {
            **result,
            "dateKey": key,
            "streakUpdated": not was_complete,
        }

    async def get_month_day_map(self, user_id: str, year: int, month: int) -> dict[str, bool]:
        if year < 2000 or year > 2100:
            raise AppError("Invalid year", status_code=400)
        if month < 1 or month > 12:
            raise AppError("Invalid month", status_code=400)

        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        range_lo = month_start - timedelta(days=14)
        range_hi = month_end + timedelta(days=14)
        documents = await self._repository.find_by_user_in_week_range(
            user_id,
            range_lo.isoformat(),
            range_hi.isoformat(),
        )

        output: dict[str, bool] = {}
        for document in documents:
            try:
                monday = date.fromisoformat(document.week_start)
            except ValueError:
                continue
            sunday = monday + timedelta(days=6)
            if sunday < month_start or monday > month_end:
                continue
            for index, day_key in enumerate(STREAK_DAY_KEYS):
                current = monday + timedelta(days=index)
                if current < month_start or current > month_end:
                    continue
                if document.week_days.get(day_key):
                    output[current.isoformat()] = True
        return output

    def _format_streak_document(self, document: object) -> dict[str, object]:
        from app.models.streak import StreakDocument

        if not isinstance(document, StreakDocument):
            raise RuntimeError("Invalid streak document")
        return {
            "weekStart": document.week_start,
            "month": document.month,
            "weekDays": self._repository.format_week_days(document.week_days),
        }
