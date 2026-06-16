"""FastAPI dependencies for services and authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.constants import HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED, HTTP_INTERNAL_SERVER_ERROR
from app.core.exceptions import AppError
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.health_service import HealthService
from app.services.admin_token_service import WebAdminTokenPayload, verify_admin_token
from app.services.token_service import verify_access_token


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repository)


def get_health_service() -> HealthService:
    return HealthService()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserDocument:
    """
    Validate Bearer JWT and load the active user.

    Mirrors Node authenticate middleware: auth failures return HTTP 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_UNAUTHORIZED,
            detail={"status": "error", "message": "Authorization token is required"},
        )

    token = authorization[len("Bearer ") :].strip()
    try:
        payload = verify_access_token(token)
    except AppError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"status": "error", "message": exc.message},
        ) from exc

    user = await user_repository.find_active_by_id(payload.user_id)
    if not user:
        raise HTTPException(
            status_code=HTTP_UNAUTHORIZED,
            detail={"status": "error", "message": "Active user not found"},
        )
    return user


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserDocument | None:
    """Load the active user when a valid Bearer JWT is present; otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[len("Bearer ") :].strip()
    try:
        payload = verify_access_token(token)
    except AppError:
        return None

    return await user_repository.find_active_by_id(payload.user_id)


async def get_web_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> WebAdminTokenPayload:
    """Validate Bearer admin JWT for dashboard routes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_UNAUTHORIZED,
            detail={"success": False, "message": "Unauthorized"},
        )

    token = authorization[len("Bearer ") :].strip()
    try:
        return verify_admin_token(token)
    except AppError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"success": False, "message": exc.message},
        ) from exc
