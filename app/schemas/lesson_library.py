"""Lesson library admin API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QuizQuestionSchema(BaseModel):
    question: str
    options: list[str]
    correct_index: int = Field(alias="correctIndex")

    model_config = {"populate_by_name": True}


class LessonPayload(BaseModel):
    lesson_code: str | None = Field(default=None, alias="lessonCode")
    day_number: int | None = Field(default=None, alias="dayNumber")
    title: str | None = None
    description: str | None = None
    level: str | None = None
    topic: str | None = None
    video_file_name: str | None = Field(default=None, alias="videoFileName")
    external_video_url: str | None = Field(default=None, alias="externalVideoUrl")
    quiz: list[QuizQuestionSchema] | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    sort_order: int | None = Field(default=None, alias="sortOrder")

    model_config = {"populate_by_name": True}


class LessonListData(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class LessonListResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: LessonListData


class LessonDataResponse(BaseModel):
    lesson: dict

    model_config = {"populate_by_name": True}


class LessonResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: LessonDataResponse


class LessonDeleteResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: None = None


class LessonVideoUploadData(BaseModel):
    file_name: str = Field(alias="fileName")
    public_url: str = Field(alias="publicUrl")
    lesson: dict

    model_config = {"populate_by_name": True}


class LessonVideoUploadResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: LessonVideoUploadData
