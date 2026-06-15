"""App configuration read/update helpers for bootstrap and web admin."""

from __future__ import annotations

from typing import Any

from app.models.app_config import (
    AppConfigDocument,
    ChatUiConfig,
    IntroVideoConfig,
    SalesVideoConfig,
)
from app.repositories.app_config_repository import AppConfigRepository
from app.utils.video_playback import playback_url_from_file_name

_repo = AppConfigRepository()


async def ensure_active_app_config() -> AppConfigDocument:
    return await _repo.ensure_active()


async def get_active_app_config() -> AppConfigDocument:
    return await _repo.ensure_active()


def _intro_video_payload(intro: IntroVideoConfig) -> dict[str, Any]:
    file_name = intro.video_file_name.strip()
    return {
        "enabled": intro.enabled,
        "showEveryLaunch": intro.show_every_launch,
        "videoFileName": file_name,
        "videoUrl": playback_url_from_file_name(file_name),
    }


def _sales_video_payload(sales: SalesVideoConfig) -> dict[str, Any]:
    file_name = sales.video_file_name.strip()
    return {
        "enabled": sales.enabled,
        "videoFileName": file_name,
        "videoUrl": playback_url_from_file_name(file_name),
    }


def app_config_to_payload(config: AppConfigDocument) -> dict[str, Any]:
    paywall = config.paywall.to_mongo()
    if not paywall["enabled"]:
        paywall["closable"] = False
    return {
        "paywall": paywall,
        "introVideo": _intro_video_payload(config.intro_video),
        "salesVideo": _sales_video_payload(config.sales_video),
        "forceUpdate": config.force_update.to_mongo(),
        "chatUi": config.chat_ui.to_mongo(),
    }


async def update_chat_ui_config(
    *,
    show_call: bool | None = None,
    show_voice: bool | None = None,
    show_mic: bool | None = None,
    show_delete_user: bool | None = None,
) -> dict[str, Any]:
    config = await get_active_app_config()
    chat = config.chat_ui
    if show_call is not None:
        chat.show_call = show_call
    if show_voice is not None:
        chat.show_voice = show_voice
    if show_mic is not None:
        chat.show_mic = show_mic
    if show_delete_user is not None:
        chat.show_delete_user = show_delete_user
    config.chat_ui = chat
    saved = await _repo.save(config)
    return app_config_to_payload(saved)


async def update_intro_video_config(
    *,
    enabled: bool | None = None,
    show_every_launch: bool | None = None,
    video_file_name: str | None = None,
) -> dict[str, Any]:
    config = await get_active_app_config()
    intro = config.intro_video
    if enabled is not None:
        intro.enabled = enabled
    if show_every_launch is not None:
        intro.show_every_launch = show_every_launch
    if video_file_name is not None:
        intro.video_file_name = video_file_name.strip()
    config.intro_video = intro
    saved = await _repo.save(config)
    return app_config_to_payload(saved)


async def update_sales_video_config(
    *,
    enabled: bool | None = None,
    video_file_name: str | None = None,
) -> dict[str, Any]:
    config = await get_active_app_config()
    sales = config.sales_video
    if enabled is not None:
        sales.enabled = enabled
    if video_file_name is not None:
        sales.video_file_name = video_file_name.strip()
    config.sales_video = sales
    saved = await _repo.save(config)
    return app_config_to_payload(saved)


async def set_intro_video_file_name(file_name: str) -> dict[str, Any]:
    return await update_intro_video_config(video_file_name=file_name)


async def set_sales_video_file_name(file_name: str) -> dict[str, Any]:
    return await update_sales_video_config(video_file_name=file_name)
