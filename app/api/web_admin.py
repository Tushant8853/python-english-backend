"""Web admin dashboard routes (Wellness-style success envelope)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_web_admin
from app.schemas.web_admin import (
    AppConfigDataResponse,
    AppConfigResponse,
    ChatUiConfigRequest,
    IntroVideoConfigRequest,
    SalesVideoConfigRequest,
    VideoUploadData,
    VideoUploadResponse,
    WebAdminLoginData,
    WebAdminLoginRequest,
    WebAdminLoginResponse,
    WebAdminOverviewResponse,
)
from app.services.admin_token_service import WebAdminTokenPayload
from app.services.app_config_service import (
    set_intro_video_file_name,
    set_sales_video_file_name,
    update_chat_ui_config,
    update_intro_video_config,
    update_sales_video_config,
)
from app.services.video_s3_service import upload_video_to_s3
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


@router.put(
    "/web-admin/chat-ui-config",
    response_model=AppConfigResponse,
    summary="Update chat UI feature flags",
)
async def web_admin_chat_ui_config(
    payload: ChatUiConfigRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
) -> AppConfigResponse:
    app_config = await update_chat_ui_config(
        show_call=payload.show_call,
        show_voice=payload.show_voice,
        show_mic=payload.show_mic,
        show_delete_user=payload.show_delete_user,
    )
    return AppConfigResponse(
        message="Chat UI config updated",
        data=AppConfigDataResponse(app_config=app_config),
    )


@router.put(
    "/web-admin/intro-video-config",
    response_model=AppConfigResponse,
    summary="Update intro video settings",
)
async def web_admin_intro_video_config(
    payload: IntroVideoConfigRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
) -> AppConfigResponse:
    app_config = await update_intro_video_config(
        enabled=payload.enabled,
        show_every_launch=payload.show_every_launch,
        video_file_name=payload.video_file_name,
    )
    return AppConfigResponse(
        message="Intro video config updated",
        data=AppConfigDataResponse(app_config=app_config),
    )


@router.post(
    "/web-admin/upload-intro-video",
    response_model=VideoUploadResponse,
    summary="Upload intro video to S3",
)
async def web_admin_upload_intro_video(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    file: UploadFile = File(...),
) -> VideoUploadResponse:
    body = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    upload = await upload_video_to_s3(body=body, mime_type=mime_type)
    app_config = await set_intro_video_file_name(upload["fileName"])
    return VideoUploadResponse(
        message="Intro video uploaded",
        data=VideoUploadData(
            file_name=upload["fileName"],
            public_url=upload["publicUrl"],
            app_config=app_config,
        ),
    )


@router.put(
    "/web-admin/sales-video-config",
    response_model=AppConfigResponse,
    summary="Update sales video settings",
)
async def web_admin_sales_video_config(
    payload: SalesVideoConfigRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
) -> AppConfigResponse:
    app_config = await update_sales_video_config(
        enabled=payload.enabled,
        video_file_name=payload.video_file_name,
    )
    return AppConfigResponse(
        message="Sales video config updated",
        data=AppConfigDataResponse(app_config=app_config),
    )


@router.post(
    "/web-admin/upload-sales-video",
    response_model=VideoUploadResponse,
    summary="Upload sales video to S3",
)
async def web_admin_upload_sales_video(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    file: UploadFile = File(...),
) -> VideoUploadResponse:
    body = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    upload = await upload_video_to_s3(body=body, mime_type=mime_type)
    app_config = await set_sales_video_file_name(upload["fileName"])
    return VideoUploadResponse(
        message="Sales video uploaded",
        data=VideoUploadData(
            file_name=upload["fileName"],
            public_url=upload["publicUrl"],
            app_config=app_config,
        ),
    )
