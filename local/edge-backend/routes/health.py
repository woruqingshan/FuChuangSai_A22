from fastapi import APIRouter

from config import settings
from models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        cloud_api_base=settings.cloud_api_base,
        request_timeout_seconds=settings.request_timeout_seconds,
    )
