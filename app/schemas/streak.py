"""Streak and progress report API schemas (Wellness-style success envelope)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WeekDaysPayload(BaseModel):
    mon: bool = False
    tue: bool = False
    wed: bool = False
    thu: bool = False
    fri: bool = False
    sat: bool = False
    sun: bool = False


class StreakStatusData(BaseModel):
    week_start: str = Field(serialization_alias="weekStart")
    week_days: WeekDaysPayload = Field(serialization_alias="weekDays")

    model_config = {"populate_by_name": True}


class StreakUpdateData(StreakStatusData):
    month: str


class StreakMonthData(BaseModel):
    days: dict[str, bool]


class StreakCheckInData(StreakUpdateData):
    date_key: str = Field(serialization_alias="dateKey")
    streak_updated: bool = Field(serialization_alias="streakUpdated")

    model_config = {"populate_by_name": True}


class SessionCompleteData(BaseModel):
    sessions_completed: int = Field(serialization_alias="sessionsCompleted")

    model_config = {"populate_by_name": True}


class ConsistencyData(BaseModel):
    consistency_percent: int = Field(serialization_alias="consistencyPercent")

    model_config = {"populate_by_name": True}


class CurrentStreakData(BaseModel):
    current_streak: int = Field(serialization_alias="currentStreak")
    longest_streak: int = Field(serialization_alias="longestStreak")
    streak_at_risk: bool = Field(serialization_alias="streakAtRisk")
    last_completed_date: str | None = Field(serialization_alias="lastCompletedDate")
    today_completed: bool = Field(serialization_alias="todayCompleted")

    model_config = {"populate_by_name": True}


class StreakStatusResponse(BaseModel):
    success: Literal[True] = True
    data: StreakStatusData


class StreakUpdateResponse(BaseModel):
    success: Literal[True] = True
    data: StreakUpdateData


class StreakMonthResponse(BaseModel):
    success: Literal[True] = True
    data: StreakMonthData


class StreakCheckInResponse(BaseModel):
    success: Literal[True] = True
    data: StreakCheckInData


class SessionCompleteResponse(BaseModel):
    success: Literal[True] = True
    data: SessionCompleteData


class ConsistencyResponse(BaseModel):
    success: Literal[True] = True
    data: ConsistencyData


class CurrentStreakResponse(BaseModel):
    success: Literal[True] = True
    data: CurrentStreakData


class UpdateStreakRequest(BaseModel):
    day: str


class CheckInStreakRequest(BaseModel):
    date_key: str | None = Field(default=None, alias="dateKey")

    model_config = {"populate_by_name": True}
