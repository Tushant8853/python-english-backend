"""Health check routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_health_service
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Returns service liveness with an ISO-8601 timestamp.",
)
async def get_api_health(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    return health_service.get_health()
