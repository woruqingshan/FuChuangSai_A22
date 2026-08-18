from fastapi import APIRouter, Response

from config import settings
from models import HealthResponse, PublicStatusResponse
from services.orchestrator_client import orchestrator_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        cloud_api_base=settings.cloud_api_base,
        cloud_ws_chat_endpoint=settings.cloud_ws_chat_endpoint or None,
        remote_transport=settings.remote_transport,
        request_timeout_seconds=settings.request_timeout_seconds,
    )


@router.get(
    "/status",
    response_model=PublicStatusResponse,
    responses={503: {"model": PublicStatusResponse}},
)
async def status(response: Response) -> PublicStatusResponse:
    ai_available = await orchestrator_client.check_health()
    if ai_available:
        return PublicStatusResponse(status="online", ai_available=True)
    response.status_code = 503
    return PublicStatusResponse(status="offline", ai_available=False)
