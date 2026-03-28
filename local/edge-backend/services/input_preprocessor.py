from models import AudioMeta, ChatRequest, RemoteChatRequest, SpeechFeatures
from services.audio import audio_turn_service


def normalize_chat_request(
    request: ChatRequest,
    session_id: str,
    turn_id: int,
    request_id: str | None = None,
) -> RemoteChatRequest:
    user_text = (request.user_text or "").strip()
    has_audio = bool(request.audio_base64)
    input_type = request.input_type or "text"

    if user_text and has_audio:
        raise ValueError("Text input and audio input cannot be submitted in the same turn.")

    if not user_text and not has_audio:
        raise ValueError("Either user_text or audio input is required.")

    if has_audio:
        processed_audio = audio_turn_service.process(
            audio_base64=request.audio_base64 or "",
            audio_format=request.audio_format,
            audio_duration_ms=request.audio_duration_ms,
            audio_sample_rate_hz=request.audio_sample_rate_hz,
            audio_channels=request.audio_channels,
            client_asr_text=request.client_asr_text,
            client_asr_source=request.client_asr_source,
            request_id=request_id,
        )
        input_type = "audio"
        user_text = processed_audio.user_text
        text_source = processed_audio.text_source
        alignment_mode = request.alignment_mode or processed_audio.alignment_mode
        audio_meta_payload = AudioMeta(**processed_audio.audio_meta.__dict__)
        speech_features_payload = SpeechFeatures(**processed_audio.speech_features.__dict__)
    else:
        text_source = request.text_source or "typed"
        alignment_mode = request.alignment_mode or "text_only"
        audio_meta_payload = request.audio_meta
        speech_features_payload = request.speech_features

    return RemoteChatRequest(
        session_id=session_id,
        turn_id=turn_id,
        user_text=user_text,
        input_type=input_type,
        client_ts=request.client_ts,
        text_source=text_source,
        client_asr_text=request.client_asr_text,
        client_asr_source=request.client_asr_source,
        audio_base64=request.audio_base64,
        audio_format=audio_meta_payload.format if audio_meta_payload else request.audio_format,
        audio_duration_ms=audio_meta_payload.duration_ms if audio_meta_payload else request.audio_duration_ms,
        audio_sample_rate_hz=(
            audio_meta_payload.sample_rate_hz if audio_meta_payload else request.audio_sample_rate_hz
        ),
        audio_channels=audio_meta_payload.channels if audio_meta_payload else request.audio_channels,
        audio_meta=audio_meta_payload,
        speech_features=speech_features_payload,
        vision_features=request.vision_features,
        alignment_mode=alignment_mode,
    )
