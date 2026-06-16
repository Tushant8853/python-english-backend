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
    intro_video_enabled: bool = Field(default=True, serialization_alias="introVideoEnabled")
    intro_video_show_every_launch: bool = Field(
        default=False,
        serialization_alias="introVideoShowEveryLaunch",
    )
    intro_video_file_name: str = Field(default="", serialization_alias="introVideoFileName")
    intro_video_url: str = Field(default="", serialization_alias="introVideoUrl")
    sales_video_enabled: bool = Field(default=False, serialization_alias="salesVideoEnabled")
    sales_video_file_name: str = Field(default="", serialization_alias="salesVideoFileName")
    sales_video_url: str = Field(default="", serialization_alias="salesVideoUrl")
    chat_ui_show_call: bool = Field(default=False, serialization_alias="chatUiShowCall")
    chat_ui_show_voice: bool = Field(default=False, serialization_alias="chatUiShowVoice")
    chat_ui_show_mic: bool = Field(default=False, serialization_alias="chatUiShowMic")
    chat_ui_show_delete_user: bool = Field(default=True, serialization_alias="chatUiShowDeleteUser")
    intake_onboarding_enabled: bool = Field(default=True, serialization_alias="intakeOnboardingEnabled")

    model_config = {"populate_by_name": True}


class IntakeOnboardingConfigRequest(BaseModel):
    enabled: bool | None = None

    model_config = {"populate_by_name": True}


class ChatUiConfigRequest(BaseModel):
    show_call: bool | None = Field(default=None, alias="showCall")
    show_voice: bool | None = Field(default=None, alias="showVoice")
    show_mic: bool | None = Field(default=None, alias="showMic")
    show_delete_user: bool | None = Field(default=None, alias="showDeleteUser")

    model_config = {"populate_by_name": True}


class IntroVideoConfigRequest(BaseModel):
    enabled: bool | None = None
    show_every_launch: bool | None = Field(default=None, alias="showEveryLaunch")
    video_file_name: str | None = Field(default=None, alias="videoFileName")

    model_config = {"populate_by_name": True}


class SalesVideoConfigRequest(BaseModel):
    enabled: bool | None = None
    video_file_name: str | None = Field(default=None, alias="videoFileName")

    model_config = {"populate_by_name": True}


class AppConfigDataResponse(BaseModel):
    app_config: dict = Field(serialization_alias="appConfig")

    model_config = {"populate_by_name": True}


class AppConfigResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: AppConfigDataResponse


class VideoUploadData(BaseModel):
    file_name: str = Field(serialization_alias="fileName")
    public_url: str = Field(serialization_alias="publicUrl")
    app_config: dict = Field(serialization_alias="appConfig")

    model_config = {"populate_by_name": True}


class VideoUploadResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: VideoUploadData


class WebAdminOverviewResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: WebAdminOverviewData
