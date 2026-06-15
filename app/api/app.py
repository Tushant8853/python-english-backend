"""Mobile app routes (bootstrap and future app-level endpoints)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_optional_user
from app.models.user import UserDocument
from app.schemas.app import BootstrapData, BootstrapResponse, BootstrapScreens
from app.services.app_config_service import get_active_app_config
from app.services.auth_service import serialize_login_user
from app.services.bootstrap_service import build_bootstrap_payload

router = APIRouter(tags=["app"])


def _parse_bool_query(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


@router.get(
    "/app/bootstrap",
    response_model=BootstrapResponse,
    summary="App bootstrap (route + remote config)",
)
async def app_bootstrap(
    intro_seen: Annotated[str | None, Query(alias="introSeen")] = None,
    paywall_skipped: Annotated[str | None, Query(alias="paywallSkipped")] = None,
    user: Annotated[UserDocument | None, Depends(get_optional_user)] = None,
) -> BootstrapResponse:
    config = await get_active_app_config()
    payload = build_bootstrap_payload(
        config=config,
        user=user,
        intro_seen=_parse_bool_query(intro_seen),
        paywall_skipped=_parse_bool_query(paywall_skipped),
    )
    route = payload["route"]
    authenticated = user is not None
    onboarding_completed = bool(user.onboarding_complete) if user else False

    return BootstrapResponse(
        message="Bootstrap loaded",
        data=BootstrapData(
            route=route,
            authenticated=authenticated,
            onboarding_completed=onboarding_completed,
            subscription_active=bool(payload["subscriptionActive"]),
            screens=BootstrapScreens(
                show_intro=route == "intro",
                show_paywall=bool(payload["screens"]["showPaywall"]),
                paywall_closable=bool(payload["screens"]["paywallClosable"]),
            ),
            app_config=payload["appConfig"],
            user=serialize_login_user(user) if user else None,
        ),
    )
