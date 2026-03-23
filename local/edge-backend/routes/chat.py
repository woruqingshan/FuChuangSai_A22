from fastapi import APIRouter, HTTPException

from models import ChatRequest, ChatResponse, ErrorResponse
from services.input_preprocessor import normalize_chat_request
from services.orchestrator_client import RemoteServiceError, orchestrator_client
from services.session_service import session_service

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = session_service.ensure_session(request.session_id)
    turn_id = session_service.ensure_turn(session_id, request.turn_id)

    try:
        remote_request = normalize_chat_request(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        response = await orchestrator_client.send_chat(remote_request)
    except RemoteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if hasattr(response, "model_copy"):
        return response.model_copy(update={"input_mode": remote_request.input_type})
    return response.copy(update={"input_mode": remote_request.input_type})
