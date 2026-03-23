from datetime import datetime, timezone

from adapters.asr_client import asr_client
from adapters.llm_client import llm_client
from adapters.tts_client import tts_client
from models import ChatRequest, ChatResponse
from services.policy_service import policy_service
from services.session_state import session_state


class DialogService:
    async def build_reply(self, request: ChatRequest) -> ChatResponse:
        transcript = await asr_client.transcribe(request)
        if not transcript:
            transcript = "The client sent an empty turn."

        memory_summary = session_state.get_summary(request.session_id)
        emotion_style = policy_service.select_emotion_style(request, transcript)
        avatar_action = policy_service.select_avatar_action(request, transcript)
        reply_text = await llm_client.generate_reply(
            request=request,
            transcript=transcript,
            memory_summary=memory_summary,
            emotion_style=emotion_style,
            avatar_action=avatar_action,
        )
        reply_audio_url = await tts_client.synthesize(reply_text)

        session_state.append_turn(request.session_id, transcript)

        return ChatResponse(
            server_status="ok",
            reply_text=reply_text,
            emotion_style=emotion_style,
            avatar_action=avatar_action,
            server_ts=int(datetime.now(timezone.utc).timestamp()),
            input_mode=request.input_type,
            reply_audio_url=reply_audio_url,
        )


dialog_service = DialogService()
