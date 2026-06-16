"""Bootstrap route resolution (multi-stage onboarding)."""

from __future__ import annotations

from typing import Any, Literal

from app.models.app_config import AppConfigDocument
from app.models.user import UserDocument
from app.services.app_config_service import app_config_to_payload

BootstrapRoute = Literal["intro", "login", "onboarding", "intake", "placement", "paywall", "home"]


def resolve_bootstrap_route(
    *,
    config: AppConfigDocument,
    user: UserDocument | None,
    intro_seen: bool,
    paywall_skipped: bool,
) -> BootstrapRoute:
    del paywall_skipped  # reserved for future paywall flow

    if user is None:
        intro = config.intro_video
        if intro.enabled and not intro_seen:
            return "intro"
        return "login"

    if not user.basic_onboarding_complete:
        return "onboarding"

    if config.intake_onboarding.enabled and not user.intake_onboarding_complete:
        return "intake"

    if not user.test_onboarding_complete:
        return "placement"

    paywall = config.paywall
    if paywall.enabled and not paywall.closable:
        return "paywall"

    return "home"


def build_bootstrap_payload(
    *,
    config: AppConfigDocument,
    user: UserDocument | None,
    intro_seen: bool,
    paywall_skipped: bool,
) -> dict[str, Any]:
    route = resolve_bootstrap_route(
        config=config,
        user=user,
        intro_seen=intro_seen,
        paywall_skipped=paywall_skipped,
    )
    app_config = app_config_to_payload(config)
    paywall_enabled = bool(app_config["paywall"]["enabled"])
    paywall_closable = bool(app_config["paywall"]["closable"]) if paywall_enabled else False
    subscription_active = False

    show_paywall = (
        route == "paywall"
        or (paywall_enabled and user is not None and not subscription_active and route == "home")
    )

    return {
        "route": route,
        "appConfig": app_config,
        "subscriptionActive": subscription_active,
        "screens": {
            "showPaywall": show_paywall,
            "paywallClosable": paywall_closable,
        },
    }
