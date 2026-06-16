"""Sync intakeOnboardingComplete when intake flow is enabled/disabled in app config."""

from __future__ import annotations

from app.models.app_config import AppConfigDocument
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.utils.onboarding_progress import sync_onboarding_complete


async def sync_user_intake_stage_for_config(
    user: UserDocument,
    config: AppConfigDocument,
    *,
    user_repository: UserRepository | None = None,
) -> UserDocument:
    """Apply intake enabled/disabled policy to the user's intake stage flag."""
    if not user.basic_onboarding_complete:
        return user

    repo = user_repository or UserRepository()
    enabled = config.intake_onboarding.enabled
    changed = False

    if not enabled:
        if not user.intake_onboarding_complete:
            user.intake_onboarding_complete = True
            changed = True
    elif user.intake_onboarding_complete and not user.intake_answers:
        user.intake_onboarding_complete = False
        changed = True

    if not changed:
        return user

    sync_onboarding_complete(user)
    return await repo.save_user(user)
