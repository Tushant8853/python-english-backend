"""Authentication routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service, get_current_user
from app.models.user import UserDocument
from app.schemas.auth import (
    CompleteOnboardingRequest,
    CompleteOnboardingResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    FirebaseLoginRequest,
    FirebaseLoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger("english_guru.auth.routes")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/firebase-login",
    response_model=FirebaseLoginResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Firebase Google login",
    description=(
        "Verify a Firebase ID token, create or update the user, optionally upsert an FCM token, "
        "and return a JWT access token."
    ),
)
async def firebase_login(
    payload: FirebaseLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> FirebaseLoginResponse:
    logger.info(
        "POST /api/auth/firebase-login",
        extra={
            "meta": {
                "hasIdToken": bool(payload.id_token),
                "platform": payload.platform,
                "hasFcmToken": bool(payload.fcm_token),
            }
        },
    )
    response = await auth_service.firebase_login(payload)
    logger.info(
        "POST /api/auth/firebase-login completed",
        extra={"meta": {"message": response.message}},
    )
    return response


@router.post(
    "/logout",
    response_model=LogoutResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Optional FCM token removal for the authenticated user. JWT is not server-blocklisted.",
)
async def logout(
    payload: LogoutRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutResponse:
    logger.info(
        "POST /api/auth/logout",
        extra={"meta": {"userId": str(current_user._id), "hasFcmToken": bool(payload.fcm_token)}},
    )
    return await auth_service.logout(current_user, payload)


@router.delete(
    "/account",
    response_model=DeleteAccountResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Delete account",
    description="Soft-delete the authenticated user (status deleted) and clear FCM tokens.",
)
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> DeleteAccountResponse:
    logger.info(
        "DELETE /api/auth/account",
        extra={"meta": {"userId": str(current_user._id), "hasFcmToken": bool(payload.fcm_token)}},
    )
    return await auth_service.delete_account(current_user, payload)


@router.post(
    "/onboarding",
    response_model=CompleteOnboardingResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Complete onboarding",
    description="Save profile fields and mark onboarding complete for the authenticated user.",
)
async def complete_onboarding(
    payload: CompleteOnboardingRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> CompleteOnboardingResponse:
    logger.info(
        "POST /api/auth/onboarding",
        extra={
            "meta": {
                "userId": str(current_user._id),
                "name": payload.name,
                "age": payload.age,
                "bestDescribesYou": payload.best_describes_you,
            }
        },
    )
    return await auth_service.complete_onboarding(current_user, payload)
