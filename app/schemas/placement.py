"""Placement test API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.intake import OnboardingStageUserSchema


class PlacementQuestionOptionSchema(BaseModel):
    id: str
    label: str


class PlacementQuestionSchema(BaseModel):
    question_key: str = Field(alias="questionKey")
    order: int
    prompt: str
    options: list[PlacementQuestionOptionSchema] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PlacementQuestionsData(BaseModel):
    language: str
    questions: list[PlacementQuestionSchema]


class PlacementQuestionsResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: PlacementQuestionsData


class PlacementAnswerInput(BaseModel):
    question_key: str = Field(alias="questionKey")
    option_id: str = Field(alias="optionId")

    model_config = {"populate_by_name": True}


class PlacementCompleteRequest(BaseModel):
    answers: list[PlacementAnswerInput]


class PlacementCompleteData(BaseModel):
    user: OnboardingStageUserSchema
    score: int
    level: str
    correct_count: int = Field(alias="correctCount")
    total_questions: int = Field(alias="totalQuestions")

    model_config = {"populate_by_name": True}


class PlacementCompleteResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: PlacementCompleteData
