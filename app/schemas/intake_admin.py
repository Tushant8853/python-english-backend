"""Web admin schemas for intake question catalog."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class IntakeOptionAdminSchema(BaseModel):
    id: str
    label: str


class IntakeLocaleAdminSchema(BaseModel):
    title: str = ""
    body: str = ""
    placeholder: str = ""
    options: list[IntakeOptionAdminSchema] = Field(default_factory=list)
    min_value: int | None = Field(default=None, alias="minValue")
    max_value: int | None = Field(default=None, alias="maxValue")

    model_config = {"populate_by_name": True}


class IntakeQuestionAdminPayload(BaseModel):
    question_key: str | None = Field(default=None, alias="questionKey")
    type: str | None = None
    order: int | None = None
    required: bool | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    content: dict[str, IntakeLocaleAdminSchema] | None = None

    model_config = {"populate_by_name": True}


class IntakeQuestionListData(BaseModel):
    items: list[dict]

    model_config = {"populate_by_name": True}


class IntakeQuestionListResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: IntakeQuestionListData


class IntakeQuestionDataResponse(BaseModel):
    question: dict

    model_config = {"populate_by_name": True}


class IntakeQuestionResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: IntakeQuestionDataResponse


class IntakeQuestionDeleteResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: None = None


class IntakeQuestionReorderRequest(BaseModel):
    ordered_ids: list[str] = Field(alias="orderedIds")

    model_config = {"populate_by_name": True}


class IntakeQuestionReorderData(BaseModel):
    items: list[dict]

    model_config = {"populate_by_name": True}


class IntakeQuestionReorderResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: IntakeQuestionReorderData
