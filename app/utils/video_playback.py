"""CloudFront playback URL helpers for intro/sales videos."""

from __future__ import annotations

from app.core.config import get_settings


def asset_base_url() -> str:
    settings = get_settings()
    base = (settings.asset_base_url or "").strip().rstrip("/")
    if base:
        return base
    domain = (settings.cloudfront_distribution_domain or "").strip().rstrip("/")
    if domain:
        return f"https://{domain}"
    return ""


def playback_url_from_file_name(file_name: str) -> str:
    cleaned = str(file_name or "").strip().lstrip("/")
    if not cleaned:
        return ""
    base = asset_base_url()
    if not base:
        return ""
    return f"{base}/{cleaned}"
