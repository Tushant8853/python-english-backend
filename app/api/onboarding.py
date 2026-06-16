"""Onboarding intake and placement routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.models.user import UserDocument
from app.schemas.intake import (
    IntakeQuestionsResponse,
    IntakeSubmitRequest,
    IntakeSubmitResponse,
)
from app.schemas.placement import (
    PlacementCompleteRequest,
    PlacementCompleteResponse,
    PlacementQuestionsResponse,
)
from app.services.intake_onboarding_service import IntakeOnboardingService
from app.services.placement_onboarding_service import PlacementOnboardingService

router = APIRouter(tags=["onboarding"])


def get_intake_service() -> IntakeOnboardingService:
    return IntakeOnboardingService()


def get_placement_service() -> PlacementOnboardingService:
    return PlacementOnboardingService()


@router.get(
    "/onboarding/intake/questions",
    response_model=IntakeQuestionsResponse,
    summary="List active dynamic intake questions",
)
async def get_intake_questions(
    _user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[IntakeOnboardingService, Depends(get_intake_service)],
    language: str | None = Query(default="en"),
) -> IntakeQuestionsResponse:
    data = await service.get_questions(language)
    return IntakeQuestionsResponse(message="Intake questions loaded", data=data)


@router.post(
    "/onboarding/intake/submit",
    response_model=IntakeSubmitResponse,
    summary="Submit dynamic intake answers",
)
async def submit_intake_answers(
    payload: IntakeSubmitRequest,
    user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[IntakeOnboardingService, Depends(get_intake_service)],
    language: str | None = Query(default="en"),
) -> IntakeSubmitResponse:
    answers = [answer.model_dump(by_alias=True) for answer in payload.answers]
    data = await service.submit_intake(user, answers, language=language)
    return IntakeSubmitResponse(message="Intake onboarding completed", data=data)


@router.get(
    "/onboarding/placement/questions",
    response_model=PlacementQuestionsResponse,
    summary="List active placement test questions",
)
async def get_placement_questions(
    _user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[PlacementOnboardingService, Depends(get_placement_service)],
    language: str | None = Query(default="en"),
) -> PlacementQuestionsResponse:
    data = await service.get_questions(language)
    return PlacementQuestionsResponse(message="Placement questions loaded", data=data)


@router.post(
    "/onboarding/placement/complete",
    response_model=PlacementCompleteResponse,
    summary="Submit placement answers and complete test stage",
)
async def complete_placement_stage(
    payload: PlacementCompleteRequest,
    user: Annotated[UserDocument, Depends(get_current_user)],
    service: Annotated[PlacementOnboardingService, Depends(get_placement_service)],
) -> PlacementCompleteResponse:
    answers = [answer.model_dump(by_alias=True) for answer in payload.answers]
    data = await service.complete_placement(user, answers)
    return PlacementCompleteResponse(message="Placement stage completed", data=data)
