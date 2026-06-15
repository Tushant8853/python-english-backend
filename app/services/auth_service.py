"""Authentication and onboarding business logic."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.constants import HTTP_BAD_REQUEST, ONBOARDING_PROFILE_OPTIONS
from app.core.exceptions import AppError
from app.models.user import UserDocument, UserProfile, upsert_fcm_token, remove_fcm_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    CompleteOnboardingRequest,
    CompleteOnboardingResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    FirebaseLoginRequest,
    FirebaseLoginResponse,
    FcmTokenResponse,
    FirebaseLoginData,
    LoginUserResponse,
    LogoutRequest,
    LogoutResponse,
    OnboardingProfileResponse,
    OnboardingUserResponse,
    CompleteOnboardingData,
)
from app.services.firebase_service import verify_firebase_id_token
from app.services.token_service import generate_access_token

logger = logging.getLogger("english_guru.auth")


class AuthService:
    """Coordinates Firebase login, logout, and onboarding flows."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def firebase_login(self, payload: FirebaseLoginRequest) -> FirebaseLoginResponse:
        id_token = payload.id_token
        logger.info(
            "Firebase login requested",
            extra={
                "meta": {
                    "hasIdToken": bool(id_token),
                    "idTokenLength": len(id_token) if isinstance(id_token, str) else 0,
                    "hasFcmToken": bool(payload.fcm_token),
                    "hasDeviceId": bool(payload.device_id),
                    "platform": payload.platform or "android(default)",
                    "termsAccepted": payload.terms_accepted or False,
                }
            },
        )

        if not id_token or not isinstance(id_token, str) or not id_token.strip():
            raise AppError("Firebase idToken is required", HTTP_BAD_REQUEST)

        firebase_user = await verify_firebase_id_token(id_token)
        user = await self._users.find_by_firebase_uid(firebase_user.uid)
        is_new_user = user is None
        now = datetime.now(UTC)

        if user is not None and user.status == "suspended":
            raise AppError("Account is suspended", HTTP_BAD_REQUEST)

        if user is not None and user.status == "deleted":
            logger.info(
                "Reactivating deleted user on login",
                extra={"meta": {"userId": str(user._id), "firebaseUid": firebase_user.uid}},
            )
            user.status = "active"
            user.last_login_at = now

        if user is None:
            user = await self._users.create_user(
                email=firebase_user.email,
                firebase_uid=firebase_user.uid,
                terms_accepted=bool(payload.terms_accepted),
            )
        else:
            user.email = firebase_user.email
            user.last_login_at = now
            if payload.terms_accepted is True and not user.terms_accepted:
                user.terms_accepted = True
                user.terms_accepted_at = now

        if payload.fcm_token and isinstance(payload.fcm_token, str) and payload.fcm_token.strip():
            platform = "ios" if payload.platform == "ios" else "android"
            upsert_fcm_token(user, payload.fcm_token, payload.device_id or "", platform)
            logger.info(
                "FCM token upserted",
                extra={
                    "meta": {
                        "userId": str(user._id),
                        "platform": platform,
                        "hasDeviceId": bool(payload.device_id),
                    }
                },
            )

        user = await self._users.save_user(user)
        access_token = generate_access_token(str(user._id))

        message = "User created and login successful" if is_new_user else "Login successful"
        logger.info(
            "Firebase login successful",
            extra={
                "meta": {
                    "userId": str(user._id),
                    "isNewUser": is_new_user,
                    "onboardingComplete": user.onboarding_complete,
                    "accessTokenLength": len(access_token),
                }
            },
        )
        return FirebaseLoginResponse(
            status="success",
            message=message,
            data=FirebaseLoginData(
                user=_serialize_login_user(user),
                access_token=access_token,
            ),
        )

    async def logout(self, user: UserDocument, payload: LogoutRequest) -> LogoutResponse:
        logger.info(
            "Logout requested",
            extra={"meta": {"userId": str(user._id), "hasFcmToken": bool(payload.fcm_token)}},
        )
        if payload.fcm_token and isinstance(payload.fcm_token, str) and payload.fcm_token.strip():
            remove_fcm_token(user, payload.fcm_token)
            await self._users.save_user(user)
            logger.info(
                "FCM token removed on logout",
                extra={"meta": {"userId": str(user._id)}},
            )

        logger.info("Logout successful", extra={"meta": {"userId": str(user._id)}})
        return LogoutResponse(status="success", message="Logout successful", data=None)

    async def delete_account(
        self,
        user: UserDocument,
        payload: DeleteAccountRequest,
    ) -> DeleteAccountResponse:
        logger.info(
            "Delete account requested",
            extra={"meta": {"userId": str(user._id), "hasFcmToken": bool(payload.fcm_token)}},
        )
        if payload.fcm_token and isinstance(payload.fcm_token, str) and payload.fcm_token.strip():
            remove_fcm_token(user, payload.fcm_token)
            await self._users.save_user(user)

        await self._users.soft_delete_user(user)
        logger.info(
            "Account deleted successfully",
            extra={"meta": {"userId": str(user._id), "email": user.email}},
        )
        return DeleteAccountResponse(status="success", message="Account deleted successfully", data=None)

    async def complete_onboarding(
        self,
        user: UserDocument,
        payload: CompleteOnboardingRequest,
    ) -> CompleteOnboardingResponse:
        logger.info(
            "Onboarding requested",
            extra={
                "meta": {
                    "userId": str(user._id),
                    "name": payload.name,
                    "age": payload.age,
                    "bestDescribesYou": payload.best_describes_you,
                }
            },
        )

        if not payload.name or not isinstance(payload.name, str) or not payload.name.strip():
            raise AppError("Name is required", HTTP_BAD_REQUEST)

        parsed_age = float(payload.age) if payload.age is not None else float("nan")
        if not (parsed_age == parsed_age and parsed_age > 0):  # NaN check via self-comparison
            raise AppError("Valid age is required", HTTP_BAD_REQUEST)

        if (
            not payload.best_describes_you
            or not isinstance(payload.best_describes_you, str)
            or payload.best_describes_you not in ONBOARDING_PROFILE_OPTIONS
        ):
            raise AppError("Valid profile type is required", HTTP_BAD_REQUEST)

        profile = UserProfile(
            name=payload.name.strip(),
            age=int(parsed_age),
            best_describes_you=payload.best_describes_you,
        )
        user = await self._users.complete_onboarding(user, profile=profile)

        logger.info(
            "Onboarding completed",
            extra={
                "meta": {
                    "userId": str(user._id),
                    "name": profile.name,
                    "age": profile.age,
                    "bestDescribesYou": profile.best_describes_you,
                }
            },
        )
        return CompleteOnboardingResponse(
            status="success",
            message="Onboarding completed",
            data=CompleteOnboardingData(
                user=OnboardingUserResponse(
                    id=str(user._id),
                    profile=OnboardingProfileResponse(
                        name=user.profile.name if user.profile else "",
                        age=user.profile.age if user.profile else None,
                        best_describes_you=user.profile.best_describes_you if user.profile else "",
                    ),
                    onboarding_complete=user.onboarding_complete,
                )
            ),
        )


def _serialize_login_user(user: UserDocument) -> LoginUserResponse:
    profile_response: OnboardingProfileResponse | None = None
    if user.profile is not None:
        profile_response = OnboardingProfileResponse(
            name=user.profile.name,
            age=user.profile.age,
            best_describes_you=user.profile.best_describes_you,
        )

    return LoginUserResponse(
        id=str(user._id),
        email=user.email,
        firebase_uid=user.firebase_uid,
        status=user.status,
        terms_accepted=user.terms_accepted,
        terms_accepted_at=user.terms_accepted_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        onboarding_complete=user.onboarding_complete,
        profile=profile_response,
        fcm_tokens=[
            FcmTokenResponse(
                token=item.token,
                device_id=item.device_id,
                platform=item.platform,
                updated_at=item.updated_at,
            )
            for item in user.fcm_tokens
        ],
    )
