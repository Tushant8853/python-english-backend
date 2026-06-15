"""Shared API response envelopes."""

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str


class ApiSuccessResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    message: str
    data: T | None = None


class MongoModel(BaseModel):
    """Serialize MongoDB-friendly values the same way Express/Mongoose does."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={},
    )
