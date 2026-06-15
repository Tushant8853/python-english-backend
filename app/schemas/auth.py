"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FirebaseLoginRequest(BaseModel):
    id_token: str | None = Field(default=None, alias="idToken")
    fcm_token: str | None = Field(default=None, alias="fcmToken")
    device_id: str | None = Field(default=None, alias="deviceId")
    platform: Literal["ios", "android"] | None = None
    terms_accepted: bool | None = Field(default=None, alias="termsAccepted")

    model_config = {"populate_by_name": True}


class LogoutRequest(BaseModel):
    fcm_token: str | None = Field(default=None, alias="fcmToken")

    model_config = {"populate_by_name": True}


class CompleteOnboardingRequest(BaseModel):
    name: str | None = None
    age: float | int | None = None
    best_describes_you: str | None = Field(default=None, alias="bestDescribesYou")

    model_config = {"populate_by_name": True}


class FcmTokenResponse(BaseModel):
    token: str
    device_id: str = Field(serialization_alias="deviceId")
    platform: Literal["ios", "android"]
    updated_at: datetime = Field(serialization_alias="updatedAt")

    model_config = {"populate_by_name": True}


class OnboardingProfileResponse(BaseModel):
    name: str
    age: int | None
    best_describes_you: str = Field(serialization_alias="bestDescribesYou")

    model_config = {"populate_by_name": True}


class LoginUserResponse(BaseModel):
    id: str
    email: str
    firebase_uid: str = Field(serialization_alias="firebaseUid")
    status: str
    terms_accepted: bool = Field(serialization_alias="termsAccepted")
    terms_accepted_at: datetime | None = Field(default=None, serialization_alias="termsAcceptedAt")
    last_login_at: datetime | None = Field(default=None, serialization_alias="lastLoginAt")
    created_at: datetime | None = Field(default=None, serialization_alias="createdAt")
    updated_at: datetime | None = Field(default=None, serialization_alias="updatedAt")
    onboarding_complete: bool = Field(default=False, serialization_alias="onboardingComplete")
    profile: OnboardingProfileResponse | None = None
    fcm_tokens: list[FcmTokenResponse] = Field(default_factory=list, serialization_alias="fcmTokens")

    model_config = {"populate_by_name": True}


class FirebaseLoginData(BaseModel):
    user: LoginUserResponse
    access_token: str = Field(serialization_alias="accessToken")

    model_config = {"populate_by_name": True}


class FirebaseLoginResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    data: FirebaseLoginData


class LogoutResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    data: None = None


class DeleteAccountRequest(BaseModel):
    fcm_token: str | None = Field(default=None, alias="fcmToken")

    model_config = {"populate_by_name": True}


class DeleteAccountResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    data: None = None


class OnboardingUserResponse(BaseModel):
    id: str
    profile: OnboardingProfileResponse
    onboarding_complete: bool = Field(serialization_alias="onboardingComplete")

    model_config = {"populate_by_name": True}


class CompleteOnboardingData(BaseModel):
    user: OnboardingUserResponse


class CompleteOnboardingResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str
    data: CompleteOnboardingData
