"""Web admin schemas for placement question catalog."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlacementOptionAdminSchema(BaseModel):
    id: str
    label: str


class PlacementLocaleAdminSchema(BaseModel):
    prompt: str = ""
    options: list[PlacementOptionAdminSchema] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PlacementQuestionAdminPayload(BaseModel):
    order: int | None = None
    correct_option_id: str | None = Field(default=None, alias="correctOptionId")
    is_active: bool | None = Field(default=None, alias="isActive")
    content: dict[str, PlacementLocaleAdminSchema] | None = None

    model_config = {"populate_by_name": True}


class PlacementQuestionListData(BaseModel):
    items: list[dict]

    model_config = {"populate_by_name": True}


class PlacementQuestionListResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: PlacementQuestionListData


class PlacementQuestionDataResponse(BaseModel):
    question: dict

    model_config = {"populate_by_name": True}


class PlacementQuestionResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: PlacementQuestionDataResponse


class PlacementQuestionDeleteResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: None = None


class PlacementQuestionReorderRequest(BaseModel):
    ordered_ids: list[str] = Field(alias="orderedIds")

    model_config = {"populate_by_name": True}


class PlacementQuestionReorderData(BaseModel):
    items: list[dict]

    model_config = {"populate_by_name": True}


class PlacementQuestionReorderResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: PlacementQuestionReorderData
