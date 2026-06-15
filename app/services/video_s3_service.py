"""Upload intro/sales videos to S3 (UUID file names)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Final

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.constants import HTTP_BAD_REQUEST, HTTP_SERVICE_UNAVAILABLE
from app.core.exceptions import AppError
from app.utils.video_playback import playback_url_from_file_name

MIME_TO_EXT: Final[dict[str, str]] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def is_s3_upload_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.aws_region
        and settings.aws_s3_bucket_name
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
    )


def _extension_for_mime(mime_type: str) -> str | None:
    return MIME_TO_EXT.get(mime_type)


def _upload_sync(*, body: bytes, mime_type: str, file_name: str) -> None:
    settings = get_settings()
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    client.put_object(
        Bucket=settings.aws_s3_bucket_name,
        Key=file_name,
        Body=body,
        ContentType=mime_type,
    )


async def upload_video_to_s3(*, body: bytes, mime_type: str) -> dict[str, str]:
    if not is_s3_upload_configured():
        raise AppError("Video upload is not configured", HTTP_SERVICE_UNAVAILABLE)

    if not body:
        raise AppError("Invalid upload", HTTP_BAD_REQUEST)

    ext = _extension_for_mime(mime_type)
    if ext is None:
        raise AppError("Invalid file type", HTTP_BAD_REQUEST)

    file_name = f"{uuid.uuid4()}{ext}"
    try:
        await asyncio.to_thread(
            _upload_sync,
            body=body,
            mime_type=mime_type,
            file_name=file_name,
        )
    except (BotoCoreError, ClientError) as exc:
        raise AppError("Video upload failed", HTTP_SERVICE_UNAVAILABLE) from exc

    return {
        "fileName": file_name,
        "publicUrl": playback_url_from_file_name(file_name),
    }
