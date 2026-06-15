"""Health check business logic."""

from datetime import UTC, datetime

from app.core.constants import MESSAGES
from app.schemas.health import HealthResponse


class HealthService:
    """Liveness probe service."""

    def get_health(self) -> HealthResponse:
        return HealthResponse(
            status="success",
            message=MESSAGES["HEALTH"]["SUCCESS"],
            timestamp=datetime.now(UTC),
        )
