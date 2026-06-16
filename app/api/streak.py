"""Streak and progress report routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_user
from app.core.exceptions import AppError
from app.models.streak import STREAK_DAY_KEYS
from app.models.user import UserDocument
from app.schemas.streak import (
    CheckInStreakRequest,
    ConsistencyData,
    ConsistencyResponse,
    CurrentStreakData,
    CurrentStreakResponse,
    SessionCompleteData,
    SessionCompleteResponse,
    StreakCheckInData,
    StreakCheckInResponse,
    StreakMonthData,
    StreakMonthResponse,
    StreakStatusData,
    StreakStatusResponse,
    StreakUpdateData,
    StreakUpdateResponse,
    UpdateStreakRequest,
    WeekDaysPayload,
)
from app.services.progress_report_service import ProgressReportService
from app.services.streak_service import StreakService

router = APIRouter(tags=["streak"])


def get_streak_service() -> StreakService:
    return StreakService()


def get_progress_report_service() -> ProgressReportService:
    return ProgressReportService()


def _to_week_days_payload(week_days: dict[str, bool]) -> WeekDaysPayload:
    return WeekDaysPayload(**{key: bool(week_days.get(key)) for key in STREAK_DAY_KEYS})


def _to_status_data(payload: dict[str, object]) -> StreakStatusData:
    week_days = payload.get("weekDays")
    if not isinstance(week_days, dict):
        week_days = {}
    return StreakStatusData(
        week_start=str(payload.get("weekStart", "")),
        week_days=_to_week_days_payload(week_days),
    )


def _to_update_data(payload: dict[str, object]) -> StreakUpdateData:
    status_data = _to_status_data(payload)
    return StreakUpdateData(
        week_start=status_data.week_start,
        week_days=status_data.week_days,
        month=str(payload.get("month", "")),
    )


@router.get(
    "/streak/status",
    response_model=StreakStatusResponse,
    summary="Current week streak status",
)
async def get_streak_status(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    streak_service: Annotated[StreakService, Depends(get_streak_service)],
) -> StreakStatusResponse:
    data = await streak_service.get_current_week_status(str(current_user._id))
    return StreakStatusResponse(data=_to_status_data(data))


@router.get(
    "/streak/month",
    response_model=StreakMonthResponse,
    summary="Completed streak days in a calendar month",
)
async def get_streak_month(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    streak_service: Annotated[StreakService, Depends(get_streak_service)],
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> StreakMonthResponse:
    days = await streak_service.get_month_day_map(str(current_user._id), year, month)
    return StreakMonthResponse(data=StreakMonthData(days=days))


@router.post(
    "/streak/update",
    response_model=StreakUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a weekday complete in the current week",
)
async def update_streak(
    payload: UpdateStreakRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    streak_service: Annotated[StreakService, Depends(get_streak_service)],
) -> StreakUpdateResponse:
    try:
        data = await streak_service.update_streak_day(str(current_user._id), payload.day)
    except AppError as exc:
        raise exc
    return StreakUpdateResponse(data=_to_update_data(data))


@router.post(
    "/streak/check-in",
    response_model=StreakCheckInResponse,
    status_code=status.HTTP_200_OK,
    summary="Daily lesson check-in (marks calendar day complete)",
)
async def check_in_streak(
    payload: CheckInStreakRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    streak_service: Annotated[StreakService, Depends(get_streak_service)],
) -> StreakCheckInResponse:
    try:
        data = await streak_service.check_in_today(str(current_user._id), payload.date_key)
    except AppError as exc:
        raise exc
    update_data = _to_update_data(data)
    return StreakCheckInResponse(
        data=StreakCheckInData(
            week_start=update_data.week_start,
            week_days=update_data.week_days,
            month=update_data.month,
            date_key=str(data.get("dateKey", "")),
            streak_updated=bool(data.get("streakUpdated")),
        ),
    )


@router.get(
    "/reports/session-complete",
    response_model=SessionCompleteResponse,
    summary="Total completed streak days (all time)",
)
async def get_session_complete_report(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    report_service: Annotated[ProgressReportService, Depends(get_progress_report_service)],
) -> SessionCompleteResponse:
    total = await report_service.get_session_complete_total(str(current_user._id))
    return SessionCompleteResponse(
        data=SessionCompleteData(sessions_completed=total),
    )


@router.get(
    "/reports/current-streak",
    response_model=CurrentStreakResponse,
    summary="Consecutive-day current streak (Snapchat-style)",
)
async def get_current_streak_report(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    report_service: Annotated[ProgressReportService, Depends(get_progress_report_service)],
) -> CurrentStreakResponse:
    report = await report_service.get_current_streak_report(str(current_user._id))
    return CurrentStreakResponse(
        data=CurrentStreakData(
            current_streak=report.current_streak,
            longest_streak=report.longest_streak,
            streak_at_risk=report.streak_at_risk,
            last_completed_date=report.last_completed_date,
            today_completed=report.today_completed,
        ),
    )


@router.get(
    "/reports/consistency",
    response_model=ConsistencyResponse,
    summary="Consistency percent for the last 28 days",
)
async def get_consistency_report(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    report_service: Annotated[ProgressReportService, Depends(get_progress_report_service)],
) -> ConsistencyResponse:
    percent = await report_service.get_consistency_percent_last_28_days(str(current_user._id))
    return ConsistencyResponse(
        data=ConsistencyData(consistency_percent=percent),
    )
