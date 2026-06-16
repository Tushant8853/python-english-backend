"""Dynamic intake onboarding schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class IntakeQuestionOptionSchema(BaseModel):
    id: str
    label: str


class IntakeQuestionSchema(BaseModel):
    question_key: str = Field(alias="questionKey")
    type: str
    order: int
    required: bool
    title: str
    body: str = ""
    placeholder: str = ""
    options: list[IntakeQuestionOptionSchema] = Field(default_factory=list)
    min_value: int | None = Field(default=None, alias="minValue")
    max_value: int | None = Field(default=None, alias="maxValue")

    model_config = {"populate_by_name": True}


class IntakeQuestionsData(BaseModel):
    language: str
    questions: list[IntakeQuestionSchema]


class IntakeQuestionsResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: IntakeQuestionsData


class IntakeAnswerInput(BaseModel):
    question_key: str = Field(alias="questionKey")
    value: str | list[str]

    model_config = {"populate_by_name": True}


class IntakeSubmitRequest(BaseModel):
    answers: list[IntakeAnswerInput]


class OnboardingStageUserSchema(BaseModel):
    id: str
    profile: dict[str, Any] | None = None
    basic_onboarding_complete: bool = Field(alias="basicOnboardingComplete")
    intake_onboarding_complete: bool = Field(alias="intakeOnboardingComplete")
    test_onboarding_complete: bool = Field(alias="testOnboardingComplete")
    onboarding_complete: bool = Field(alias="onboardingComplete")
    placement_score: int | None = Field(default=None, alias="placementScore")
    placement_level: str | None = Field(default=None, alias="placementLevel")

    model_config = {"populate_by_name": True}


class IntakeSubmitData(BaseModel):
    user: OnboardingStageUserSchema


class IntakeSubmitResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: IntakeSubmitData
