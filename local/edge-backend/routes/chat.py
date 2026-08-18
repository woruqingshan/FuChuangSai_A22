import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from config import settings
from models import ChatJobAcceptedResponse, ChatRequest, ErrorResponse
from services.access_service import AccessError, access_service
from services.job_manager import JobError, job_manager
from services.input_preprocessor import normalize_chat_request
from services.observability import edge_observability
from services.rate_limiter import rate_limiter
from services.request_context import get_client_ip
from services.session_service import SessionError, session_service

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat(http_request: Request, request: ChatRequest) -> ChatJobAcceptedResponse:
    request_id = uuid4().hex[:12]
    started_at = time.perf_counter()
    try:
        session_record = session_service.require_session(http_request.cookies.get(settings.session_cookie_name))
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    try:
        access_service.require_access(
            session=session_record,
            access_token=http_request.cookies.get(settings.access_cookie_name),
        )
    except AccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    client_ip = get_client_ip(http_request)
    session_limit = rate_limiter.allow(
        f"chat:session:{session_record.session_id}",
        limit=settings.chat_session_rate_limit_count,
        window_seconds=settings.chat_session_rate_limit_window_seconds,
    )
    if not session_limit.allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "rate_limited", "message": "Too many chat requests for this session."},
            headers={"Retry-After": str(session_limit.retry_after_seconds)},
        )
    ip_limit = rate_limiter.allow(
        f"chat:ip:{client_ip}",
        limit=settings.chat_ip_rate_limit_count,
        window_seconds=settings.chat_ip_rate_limit_window_seconds,
    )
    if not ip_limit.allowed:
        raise HTTPException(
            status_code=429,
            detail={"reason": "rate_limited", "message": "Too many chat requests."},
            headers={"Retry-After": str(ip_limit.retry_after_seconds)},
        )

    turn_id = session_service.allocate_turn(session_record)
    session_id = session_record.session_id
    canonical_turn_window = session_service.canonical_turn_time_window(
        record=session_record,
        turn_id=turn_id,
        client_window=request.turn_time_window,
    )
    if hasattr(request, "model_copy"):
        server_request = request.model_copy(
            update={
                "session_id": session_id,
                "turn_id": turn_id,
                "turn_time_window": canonical_turn_window,
            }
        )
    else:
        server_request = request.copy(
            update={
                "session_id": session_id,
                "turn_id": turn_id,
                "turn_time_window": canonical_turn_window,
            }
        )
    edge_observability.log_chat_request_received(
        request_id,
        {
            "session_id": session_id,
            "turn_id": turn_id,
            "input_type": server_request.input_type,
            "avatar_profile_id": server_request.avatar_profile_id,
            "has_audio": bool(server_request.audio_base64),
            "has_video": bool(server_request.video_frames or server_request.video_meta),
            "has_turn_time_window": bool(server_request.turn_time_window),
            "user_text_length": len((server_request.user_text or "").strip()),
        },
    )

    try:
        remote_request = normalize_chat_request(
            request=server_request,
            session_id=session_id,
            turn_id=turn_id,
            request_id=request_id,
        )
    except ValueError as exc:
        edge_observability.log_chat_error(
            request_id,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            detail=str(exc),
            status_code=400,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    edge_observability.log_chat_request_prepared(
        request_id,
        {
            "session_id": remote_request.session_id,
            "turn_id": remote_request.turn_id,
            "input_type": remote_request.input_type,
            "text_source": remote_request.text_source,
            "alignment_mode": remote_request.alignment_mode,
            "avatar_profile_id": remote_request.avatar_profile_id,
            "has_audio": bool(remote_request.audio_base64),
            "has_video": bool(remote_request.video_frames or remote_request.video_meta),
            "client_asr_text": remote_request.client_asr_text,
            "resolved_user_text": remote_request.user_text,
            "turn_window_id": (
                remote_request.turn_time_window.window_id if remote_request.turn_time_window else None
            ),
            "video_frame_count": len(remote_request.video_frames),
            "speech_tags": (
                remote_request.speech_features.emotion_tags if remote_request.speech_features else []
            ),
        },
    )

    try:
        job = await job_manager.submit(session_id=session_id, turn_id=turn_id, request=remote_request)
    except JobError as exc:
        edge_observability.log_chat_error(
            request_id,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            detail=exc.detail,
            status_code=exc.status_code,
        )
        if exc.status_code == 409:
            raise HTTPException(
                status_code=409,
                detail={"reason": "active_job", "message": exc.detail, "job_id": exc.job_id},
            ) from exc
        if exc.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail={"reason": "queue_full", "message": "Public generation queue is full."},
            ) from exc
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    edge_observability.log_chat_response(
        request_id,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        payload={
            "session_id": job.session_id,
            "turn_id": job.turn_id,
            "job_id": job.job_id,
            "job_status": job.status,
        },
    )
    return ChatJobAcceptedResponse(
        job_id=job.job_id,
        status=job.status,
        queue_position=await job_manager.queue_position(job.job_id),
    )
