from fastapi import APIRouter, HTTPException

from models import ChatRequest, ChatResponse, ErrorResponse
from services.dialog_service import dialog_service

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}},
)
async def chat(request: ChatRequest) -> ChatResponse:
    has_text = bool(request.user_text.strip())
    has_audio = bool(request.audio_base64)
    if not has_text and not has_audio:
        raise HTTPException(status_code=400, detail="Either user_text or audio input is required.")

    return await dialog_service.build_reply(request)
