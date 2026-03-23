from models import ChatRequest, RemoteChatRequest


def normalize_chat_request(
    request: ChatRequest,
    session_id: str,
    turn_id: int,
) -> RemoteChatRequest:
    user_text = (request.user_text or "").strip()
    has_audio = bool(request.audio_base64)
    input_type = request.input_type or "text"

    if not user_text and not has_audio:
        raise ValueError("Either user_text or audio input is required.")

    if not user_text and has_audio:
        # Keep the first audio pipeline contract-compatible until remote ASR is added.
        user_text = "Audio message received from local client."

    if has_audio and input_type == "text":
        input_type = "audio"

    return RemoteChatRequest(
        session_id=session_id,
        turn_id=turn_id,
        user_text=user_text,
        input_type=input_type,
        client_ts=request.client_ts,
        audio_base64=request.audio_base64,
        audio_format=request.audio_format,
        audio_duration_ms=request.audio_duration_ms,
    )
