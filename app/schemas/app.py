"""Mobile app bootstrap schemas (Wellness-style success envelope)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.auth import LoginUserResponse


class BootstrapScreens(BaseModel):
    show_intro: bool = Field(serialization_alias="showIntro")
    show_paywall: bool = Field(serialization_alias="showPaywall")
    paywall_closable: bool = Field(serialization_alias="paywallClosable")

    model_config = {"populate_by_name": True}


class BootstrapData(BaseModel):
    route: Literal["intro", "login", "onboarding", "intake", "placement", "paywall", "home"]
    authenticated: bool
    onboarding_completed: bool = Field(serialization_alias="onboardingCompleted")
    subscription_active: bool = Field(serialization_alias="subscriptionActive")
    screens: BootstrapScreens
    app_config: dict[str, Any] = Field(serialization_alias="appConfig")
    user: LoginUserResponse | None = None

    model_config = {"populate_by_name": True}


class BootstrapResponse(BaseModel):
    success: Literal[True] = True
    message: str
    data: BootstrapData
