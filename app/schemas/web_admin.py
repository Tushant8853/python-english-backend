"""Web admin dashboard request and response schemas (Wellness-style envelope)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WebAdminLoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class WebAdminLoginData(BaseModel):
    token: str


class WebAdminLoginResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: WebAdminLoginData


class WebAdminOverviewData(BaseModel):
    total_users: int = Field(serialization_alias="totalUsers")
    active_users: int = Field(serialization_alias="activeUsers")
    deleted_users: int = Field(serialization_alias="deletedUsers")
    suspended_users: int = Field(serialization_alias="suspendedUsers")
    onboarding_completed_users: int = Field(serialization_alias="onboardingCompletedUsers")
    generated_at: datetime = Field(serialization_alias="generatedAt")

    model_config = {"populate_by_name": True}


class WebAdminOverviewResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: WebAdminOverviewData
