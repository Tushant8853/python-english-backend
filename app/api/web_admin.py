"""Web admin dashboard routes (Wellness-style success envelope)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_web_admin
from app.schemas.web_admin import (
    WebAdminLoginData,
    WebAdminLoginRequest,
    WebAdminLoginResponse,
    WebAdminOverviewResponse,
)
from app.services.admin_token_service import WebAdminTokenPayload
from app.services.web_admin_service import admin_login, get_overview

router = APIRouter(tags=["web-admin"])


@router.post(
    "/web-admin/login",
    response_model=WebAdminLoginResponse,
    summary="Web admin login",
)
async def web_admin_login(payload: WebAdminLoginRequest) -> WebAdminLoginResponse:
    username = (payload.username or "").strip()
    password = payload.password or ""
    token = admin_login(username, password)
    return WebAdminLoginResponse(
        message="Login successful",
        data=WebAdminLoginData(token=token),
    )


@router.get(
    "/web-admin/overview",
    response_model=WebAdminOverviewResponse,
    summary="Web admin overview stats",
)
async def web_admin_overview(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
) -> WebAdminOverviewResponse:
    data = await get_overview()
    return WebAdminOverviewResponse(
        message="Overview loaded",
        data=data,
    )
