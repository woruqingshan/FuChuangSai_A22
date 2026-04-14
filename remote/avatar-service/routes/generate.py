import math
import wave

from fastapi import APIRouter

from models import GenerateRequest, GenerateResponse
from services.avatar_render_bridge import avatar_render_bridge
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
        instruct_text=request.tts_instruct_text,
        speed=request.tts_speed,
        speaker_id=request.tts_speaker_id,
    )
    reply_video_path = None

    if settings.avatar_renderer_backend == "echomimic_v2" and settings.echomimic_root and reply_audio_url:
        audio_path = avatar_storage.get_audio_path(session_id=request.session_id, turn_id=request.turn_id)
        estimated_duration_ms = _resolve_audio_duration_ms(audio_path, fallback_ms=estimated_duration_ms)
        render_fps = 24
        settle_tail_ms = 900
        render_duration_ms = estimated_duration_ms + settle_tail_ms
        render_length = max(60, math.ceil((render_duration_ms / 1000.0) * render_fps) + 6)
        render_request = avatar_render_bridge.build_request(
            session_id=request.session_id,
            turn_id=request.turn_id,
            audio_path=str(audio_path),
            ref_image_path=request.ref_image_path or settings.echomimic_ref_image_path,
            emotion_style=request.emotion_style,
            pose_dir=request.pose_dir or settings.echomimic_pose_dir or None,
            fps=render_fps,
            length=render_length,
        )
        render_result = avatar_render_bridge.render_video(
            render_request,
            workdir=settings.echomimic_root,
            infer_script=settings.echomimic_infer_script,
            timeout_seconds=settings.echomimic_timeout_seconds,
        )
        persisted_video_path = avatar_storage.persist_video(
            session_id=request.session_id,
            turn_id=request.turn_id,
            source_path=render_result.video_path,
        )
        reply_video_path = str(persisted_video_path)

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
        reply_video_path=reply_video_path,
        reply_video_url=(
            f"/media/video/{request.session_id}/{request.turn_id}"
            if reply_video_path
            else None
        ),
    )


def _resolve_audio_duration_ms(audio_path, *, fallback_ms: int) -> int:
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
        if sample_rate <= 0:
            return fallback_ms
        return max(fallback_ms, math.ceil((frame_count / sample_rate) * 1000))
    except Exception:
        return fallback_ms
