"""Web admin dashboard routes (Wellness-style success envelope)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.dependencies import get_web_admin
from app.schemas.web_admin import (
    AppConfigDataResponse,
    AppConfigResponse,
    ChatUiConfigRequest,
    IntroVideoConfigRequest,
    IntakeOnboardingConfigRequest,
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
    update_intake_onboarding_config,
    update_sales_video_config,
)
from app.schemas.intake_admin import (
    IntakeQuestionAdminPayload,
    IntakeQuestionDeleteResponse,
    IntakeQuestionListResponse,
    IntakeQuestionReorderRequest,
    IntakeQuestionReorderResponse,
    IntakeQuestionResponse,
)
from app.schemas.placement_admin import (
    PlacementQuestionAdminPayload,
    PlacementQuestionDeleteResponse,
    PlacementQuestionListResponse,
    PlacementQuestionReorderRequest,
    PlacementQuestionReorderResponse,
    PlacementQuestionResponse,
)
from app.schemas.lesson_library import (
    LessonDeleteResponse,
    LessonListResponse,
    LessonPayload,
    LessonResponse,
    LessonVideoUploadResponse,
)
from app.services.intake_question_admin_service import IntakeQuestionAdminService
from app.services.placement_question_admin_service import PlacementQuestionAdminService
from app.services.lesson_library_service import LessonLibraryService
from app.services.video_s3_service import upload_video_to_s3
from app.services.web_admin_service import admin_login, get_overview

router = APIRouter(tags=["web-admin"])


def get_lesson_library_service() -> LessonLibraryService:
    return LessonLibraryService()


def get_intake_question_admin_service() -> IntakeQuestionAdminService:
    return IntakeQuestionAdminService()


def get_placement_question_admin_service() -> PlacementQuestionAdminService:
    return PlacementQuestionAdminService()


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
    "/web-admin/intake-onboarding-config",
    response_model=AppConfigResponse,
    summary="Enable or disable mobile intake onboarding",
)
async def web_admin_intake_onboarding_config(
    payload: IntakeOnboardingConfigRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
) -> AppConfigResponse:
    app_config = await update_intake_onboarding_config(enabled=payload.enabled)
    return AppConfigResponse(
        message="Intake onboarding config updated",
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


@router.get(
    "/web-admin/lessons",
    response_model=LessonListResponse,
    summary="List lesson library catalog",
)
async def web_admin_list_lessons(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
    page: int = 1,
    page_size: int = Query(20, alias="pageSize"),
    level: str | None = None,
    topic: str | None = None,
    is_active: bool | None = None,
) -> LessonListResponse:
    data = await service.list_lessons(
        level=level,
        topic=topic,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return LessonListResponse(message="Lessons loaded", data=data)


@router.get(
    "/web-admin/lessons/{lesson_id}",
    response_model=LessonResponse,
    summary="Get one lesson",
)
async def web_admin_get_lesson(
    lesson_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
) -> LessonResponse:
    lesson = await service.get_lesson(lesson_id)
    return LessonResponse(message="Lesson loaded", data={"lesson": lesson})


@router.post(
    "/web-admin/lessons",
    response_model=LessonResponse,
    summary="Create lesson",
)
async def web_admin_create_lesson(
    payload: LessonPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
) -> LessonResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.quiz is not None:
        body["quiz"] = [q.model_dump(by_alias=True) for q in payload.quiz]
    lesson = await service.create_lesson(body)
    return LessonResponse(message="Lesson created", data={"lesson": lesson})


@router.put(
    "/web-admin/lessons/{lesson_id}",
    response_model=LessonResponse,
    summary="Update lesson",
)
async def web_admin_update_lesson(
    lesson_id: str,
    payload: LessonPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
) -> LessonResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.quiz is not None:
        body["quiz"] = [q.model_dump(by_alias=True) for q in payload.quiz]
    lesson = await service.update_lesson(lesson_id, body)
    return LessonResponse(message="Lesson updated", data={"lesson": lesson})


@router.delete(
    "/web-admin/lessons/{lesson_id}",
    response_model=LessonDeleteResponse,
    summary="Delete lesson",
)
async def web_admin_delete_lesson(
    lesson_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
) -> LessonDeleteResponse:
    await service.delete_lesson(lesson_id)
    return LessonDeleteResponse(message="Lesson deleted")


@router.post(
    "/web-admin/lessons/{lesson_id}/upload-video",
    response_model=LessonVideoUploadResponse,
    summary="Upload lesson video to S3",
)
async def web_admin_upload_lesson_video(
    lesson_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[LessonLibraryService, Depends(get_lesson_library_service)],
    file: UploadFile = File(...),
) -> LessonVideoUploadResponse:
    body = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    upload = await upload_video_to_s3(body=body, mime_type=mime_type)
    lesson = await service.set_lesson_video_file_name(lesson_id, upload["fileName"])
    return LessonVideoUploadResponse(
        message="Lesson video uploaded",
        data={
            "fileName": upload["fileName"],
            "publicUrl": upload["publicUrl"],
            "lesson": lesson,
        },
    )


@router.get(
    "/web-admin/intake-questions",
    response_model=IntakeQuestionListResponse,
    summary="List intake onboarding questions",
)
async def web_admin_list_intake_questions(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionListResponse:
    data = await service.list_questions()
    return IntakeQuestionListResponse(message="Intake questions loaded", data=data)


@router.get(
    "/web-admin/intake-questions/{question_id}",
    response_model=IntakeQuestionResponse,
    summary="Get one intake question",
)
async def web_admin_get_intake_question(
    question_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionResponse:
    question = await service.get_question(question_id)
    return IntakeQuestionResponse(message="Intake question loaded", data={"question": question})


@router.post(
    "/web-admin/intake-questions",
    response_model=IntakeQuestionResponse,
    summary="Create intake question",
)
async def web_admin_create_intake_question(
    payload: IntakeQuestionAdminPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.content is not None:
        body["content"] = {
            lang: block.model_dump(by_alias=True)
            for lang, block in payload.content.items()
        }
    question = await service.create_question(body)
    return IntakeQuestionResponse(message="Intake question created", data={"question": question})


@router.put(
    "/web-admin/intake-questions/reorder",
    response_model=IntakeQuestionReorderResponse,
    summary="Reorder intake questions",
)
async def web_admin_reorder_intake_questions(
    payload: IntakeQuestionReorderRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionReorderResponse:
    data = await service.reorder_questions(payload.ordered_ids)
    return IntakeQuestionReorderResponse(message="Intake questions reordered", data=data)


@router.put(
    "/web-admin/intake-questions/{question_id}",
    response_model=IntakeQuestionResponse,
    summary="Update intake question",
)
async def web_admin_update_intake_question(
    question_id: str,
    payload: IntakeQuestionAdminPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.content is not None:
        body["content"] = {
            lang: block.model_dump(by_alias=True)
            for lang, block in payload.content.items()
        }
    question = await service.update_question(question_id, body)
    return IntakeQuestionResponse(message="Intake question updated", data={"question": question})


@router.delete(
    "/web-admin/intake-questions/{question_id}",
    response_model=IntakeQuestionDeleteResponse,
    summary="Delete intake question",
)
async def web_admin_delete_intake_question(
    question_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[IntakeQuestionAdminService, Depends(get_intake_question_admin_service)],
) -> IntakeQuestionDeleteResponse:
    await service.delete_question(question_id)
    return IntakeQuestionDeleteResponse(message="Intake question deleted")


@router.get(
    "/web-admin/placement-questions",
    response_model=PlacementQuestionListResponse,
    summary="List placement test questions",
)
async def web_admin_list_placement_questions(
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionListResponse:
    data = await service.list_questions()
    return PlacementQuestionListResponse(message="Placement questions loaded", data=data)


@router.get(
    "/web-admin/placement-questions/{question_id}",
    response_model=PlacementQuestionResponse,
    summary="Get one placement question",
)
async def web_admin_get_placement_question(
    question_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionResponse:
    question = await service.get_question(question_id)
    return PlacementQuestionResponse(message="Placement question loaded", data={"question": question})


@router.post(
    "/web-admin/placement-questions",
    response_model=PlacementQuestionResponse,
    summary="Create placement question",
)
async def web_admin_create_placement_question(
    payload: PlacementQuestionAdminPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.content is not None:
        body["content"] = {
            lang: block.model_dump(by_alias=True)
            for lang, block in payload.content.items()
        }
    question = await service.create_question(body)
    return PlacementQuestionResponse(message="Placement question created", data={"question": question})


@router.put(
    "/web-admin/placement-questions/reorder",
    response_model=PlacementQuestionReorderResponse,
    summary="Reorder placement questions",
)
async def web_admin_reorder_placement_questions(
    payload: PlacementQuestionReorderRequest,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionReorderResponse:
    data = await service.reorder_questions(payload.ordered_ids)
    return PlacementQuestionReorderResponse(message="Placement questions reordered", data=data)


@router.put(
    "/web-admin/placement-questions/{question_id}",
    response_model=PlacementQuestionResponse,
    summary="Update placement question",
)
async def web_admin_update_placement_question(
    question_id: str,
    payload: PlacementQuestionAdminPayload,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionResponse:
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.content is not None:
        body["content"] = {
            lang: block.model_dump(by_alias=True)
            for lang, block in payload.content.items()
        }
    question = await service.update_question(question_id, body)
    return PlacementQuestionResponse(message="Placement question updated", data={"question": question})


@router.delete(
    "/web-admin/placement-questions/{question_id}",
    response_model=PlacementQuestionDeleteResponse,
    summary="Delete placement question",
)
async def web_admin_delete_placement_question(
    question_id: str,
    _admin: Annotated[WebAdminTokenPayload, Depends(get_web_admin)],
    service: Annotated[PlacementQuestionAdminService, Depends(get_placement_question_admin_service)],
) -> PlacementQuestionDeleteResponse:
    await service.delete_question(question_id)
    return PlacementQuestionDeleteResponse(message="Placement question deleted")
