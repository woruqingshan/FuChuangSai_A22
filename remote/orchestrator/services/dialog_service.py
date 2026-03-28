import time
from datetime import datetime, timezone

from adapters.asr_client import asr_client
from adapters.llm_client import LLMRequest, llm_client
from adapters.tts_client import tts_client
from config import settings
from models import ChatRequest, ChatResponse
from services.alignment import multimodal_alignment_service
from services.observability import orchestrator_observability
from services.policy_service import policy_service
from services.prompt_builder import prompt_builder
from services.session_state import session_state


class DialogService:
    async def build_reply(self, request: ChatRequest) -> ChatResponse:
        started_at = time.perf_counter()
        transcript = await asr_client.transcribe(request)
        if not transcript:
            transcript = "The client sent an empty turn."

        aligned_turn = multimodal_alignment_service.align(request, transcript)
        orchestrator_observability.log_alignment_ready(
            request.session_id,
            request.turn_id,
            {
                "alignment_mode": aligned_turn.alignment_mode,
                "alignment_summary": aligned_turn.alignment_summary,
                "speech_context_ready": bool(aligned_turn.speech_context),
                "vision_context_ready": bool(aligned_turn.vision_context),
            },
        )
        context_messages = session_state.build_context_messages(request.session_id)
        memory_summary = session_state.get_summary(request.session_id)
        system_prompt = prompt_builder.build_system_prompt(
            settings.system_prompt,
            context_summary=memory_summary,
        )
        emotion_style = policy_service.select_emotion_style(request, transcript)
        avatar_action = policy_service.select_avatar_action(request, transcript)
        llm_result = await llm_client.generate_reply(
            LLMRequest(
                session_id=request.session_id,
                turn_id=request.turn_id,
                system_prompt=system_prompt,
                user_text=aligned_turn.llm_user_text,
                input_mode=request.input_type,
                context_messages=context_messages,
                context_summary=memory_summary,
            )
        )
        reply_audio_url = await tts_client.synthesize(llm_result.reply_text)
        avatar_output = policy_service.build_avatar_output(
            request=request,
            emotion_style=emotion_style,
            avatar_action=avatar_action,
            reply_text=llm_result.reply_text,
            reply_audio_url=reply_audio_url,
        )

        session_state.append_message(
            request.session_id,
            role="user",
            content=aligned_turn.canonical_user_text,
            turn_id=request.turn_id,
            input_mode=request.input_type,
        )
        session_state.append_message(
            request.session_id,
            role="assistant",
            content=llm_result.reply_text,
            turn_id=request.turn_id,
            input_mode="text",
        )

        response = ChatResponse(
            server_status="ok",
            reply_text=llm_result.reply_text,
            emotion_style=emotion_style,
            avatar_action=avatar_action,
            avatar_output=avatar_output,
            server_ts=int(datetime.now(timezone.utc).timestamp()),
            input_mode=request.input_type,
            reply_audio_url=reply_audio_url,
            response_source=llm_result.response_source,
            context_summary=memory_summary or None,
            reasoning_hint=llm_result.reasoning_hint
            or aligned_turn.alignment_summary
            or prompt_builder.build_reasoning_hint(context_messages),
            turn_time_window=request.turn_time_window,
            alignment_mode=aligned_turn.alignment_mode,
        )
        orchestrator_observability.log_chat_response(
            request.session_id,
            request.turn_id,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            payload={
                "response_source": response.response_source,
                "alignment_mode": response.alignment_mode,
                "emotion_style": response.emotion_style,
                "reply_text_preview": response.reply_text[:200],
            },
        )
        return response


dialog_service = DialogService()
