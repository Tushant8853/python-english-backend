"""Health check response schema."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """GET /api/health payload (no data wrapper)."""

    status: Literal["success"] = "success"
    message: str
    timestamp: datetime = Field(description="Server time in ISO-8601")
