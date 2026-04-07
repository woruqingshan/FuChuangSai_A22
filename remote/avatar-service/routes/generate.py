from fastapi import APIRouter

from models import GenerateRequest, GenerateResponse
from services.expression_generator import expression_generator
from services.motion_generator import motion_generator
from services.storage import avatar_storage
from services.tts_runtime import tts_runtime
from services.viseme_generator import viseme_generator
from config import settings

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    estimated_duration_ms = min(max(len(request.reply_text) * 180, 1200), 8000)
    reply_audio_url = tts_runtime.synthesize(
        session_id=request.session_id,
        turn_id=request.turn_id,
        text=request.reply_text,
    )

    avatar_output = {
        "contract_version": "v1",
        "renderer_mode": settings.renderer_mode,
        "transport_mode": settings.transport_mode,
        "websocket_endpoint": settings.websocket_endpoint,
        "stream_id": request.turn_time_window.stream_id if request.turn_time_window else None,
        "sequence_id": request.turn_id,
        "avatar_id": settings.avatar_id,
        "emotion_style": request.emotion_style,
        "audio": {
            "audio_url": reply_audio_url,
            "mime_type": "audio/wav" if reply_audio_url else None,
            "duration_ms": estimated_duration_ms if reply_audio_url else None,
            "cache_key": f"{request.session_id}:{request.turn_id}:tts" if reply_audio_url else None,
        },
        "viseme_seq": viseme_generator.generate(
            text=request.reply_text,
            duration_ms=estimated_duration_ms,
        ),
        "expression_seq": expression_generator.generate(
            expression=request.avatar_action.facial_expression,
            duration_ms=estimated_duration_ms,
        ),
        "motion_seq": motion_generator.generate(
            motion=request.avatar_action.head_motion,
            duration_ms=estimated_duration_ms,
        ),
    }

    avatar_storage.persist_output(
        session_id=request.session_id,
        turn_id=request.turn_id,
        payload=avatar_output,
    )

    return GenerateResponse(
        avatar_output=avatar_output,
        reply_audio_url=reply_audio_url,
    )
