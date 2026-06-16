"""Onboarding stage flags and derived onboardingComplete."""

from __future__ import annotations

from typing import Any

from app.models.user import UserDocument


def sync_onboarding_complete(user: UserDocument) -> None:
    """Derive onboardingComplete from the three stage flags only."""
    user.onboarding_complete = (
        user.basic_onboarding_complete
        and user.intake_onboarding_complete
        and user.test_onboarding_complete
    )


def read_onboarding_flags_from_mongo(raw: dict[str, Any]) -> tuple[bool, bool, bool, bool]:
    """Load stage flags; migrate legacy users who only had onboardingComplete."""
    if "basicOnboardingComplete" in raw:
        basic = bool(raw.get("basicOnboardingComplete"))
        intake = bool(raw.get("intakeOnboardingComplete"))
        test = bool(raw.get("testOnboardingComplete"))
        complete = bool(raw.get("onboardingComplete"))
        derived = basic and intake and test
        if complete != derived:
            complete = derived
        return basic, intake, test, complete

    legacy_complete = bool(raw.get("onboardingComplete", False))
    if legacy_complete:
        return True, True, True, True
    return False, False, False, False
