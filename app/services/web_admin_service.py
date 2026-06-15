"""Web admin login and overview analytics."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.constants import HTTP_SERVICE_UNAVAILABLE, HTTP_UNAUTHORIZED
from app.core.exceptions import AppError
from app.database.connection import get_database
from app.schemas.web_admin import WebAdminOverviewData
from app.services.admin_token_service import generate_admin_token


def _timing_safe_equal(left: str, right: str) -> bool:
    left_bytes = left.encode("utf-8")
    right_bytes = right.encode("utf-8")
    if len(left_bytes) != len(right_bytes):
        return False
    return hmac.compare_digest(left_bytes, right_bytes)


def admin_login(username: str, password: str) -> str:
    settings = get_settings()
    configured_username = (settings.admin_username or "").strip()
    configured_password = settings.admin_password or ""
    admin_secret = (settings.admin_jwt_secret or "").strip()

    if not configured_username or not configured_password or not admin_secret:
        raise AppError("Admin login is not configured", HTTP_SERVICE_UNAVAILABLE)

    if not _timing_safe_equal(username.strip(), configured_username) or not _timing_safe_equal(
        password, configured_password
    ):
        raise AppError("Invalid credentials", HTTP_UNAUTHORIZED)

    return generate_admin_token(configured_username)


async def get_overview() -> WebAdminOverviewData:
    collection = get_database()["users"]
    total_users = await collection.count_documents({})
    active_users = await collection.count_documents({"status": "active"})
    deleted_users = await collection.count_documents({"status": "deleted"})
    suspended_users = await collection.count_documents({"status": "suspended"})
    onboarding_completed_users = await collection.count_documents(
        {"status": "active", "onboardingComplete": True}
    )

    return WebAdminOverviewData(
        total_users=total_users,
        active_users=active_users,
        deleted_users=deleted_users,
        suspended_users=suspended_users,
        onboarding_completed_users=onboarding_completed_users,
        generated_at=datetime.now(UTC),
    )
