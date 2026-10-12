import re
from typing import Protocol

import httpx

from config import settings
from models import ContextMessage


class LLMRequest:
    def __init__(
        self,
        *,
        session_id: str,
        turn_id: int,
        system_prompt: str,
        user_text: str,
        input_mode: str,
        context_messages: list[ContextMessage],
        context_summary: str,
        response_language: str | None = None,
        ui_language: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.turn_id = turn_id
        self.system_prompt = system_prompt
        self.user_text = user_text
        self.input_mode = input_mode
        self.context_messages = context_messages
        self.context_summary = context_summary
        self.response_language = response_language
        self.ui_language = ui_language


class LLMResult:
    def __init__(
        self,
        *,
        reply_text: str,
        response_source: str,
        reasoning_hint: str | None = None,
    ) -> None:
        self.reply_text = reply_text
        self.response_source = response_source
        self.reasoning_hint = reasoning_hint


class BaseLLMProvider(Protocol):
    provider_name: str

    async def complete(self, request: LLMRequest) -> LLMResult:
        ...


class MockLLMProvider:
    provider_name = "mock"

    async def complete(self, request: LLMRequest) -> LLMResult:
        lowered = request.user_text.lower()
        spanish = request.response_language == "Spanish"

        emotional_keywords = [
            "sad", "unhappy", "stressed", "triste", "ansioso", "ansiosa",
            "preocupado", "preocupada", "压力", "焦虑", "难过", "不开心",
        ]
        if any(keyword in lowered for keyword in emotional_keywords):
            return LLMResult(
                reply_text=(
                    "Estoy aquí contigo. Tómate tu tiempo; quiero escuchar "
                    "lo que más te preocupa ahora."
                    if spanish
                    else "I'm here with you. Take your time; I'm listening to "
                    "what matters most to you right now."
                ),
                response_source="mock",
                reasoning_hint="detected-emotional-keywords",
            )

        if request.input_mode == "audio":
            return LLMResult(
                reply_text=(
                    "Te escucho. Tómate tu tiempo y cuéntame qué tienes en mente."
                    if spanish
                    else "I heard you. Take your time, and tell me what's on your mind."
                ),
                response_source="mock",
                reasoning_hint="audio-placeholder",
            )

        if request.context_summary:
            return LLMResult(
                reply_text=(
                    "Recuerdo lo que compartiste antes. Podemos seguir hablando "
                    "cuando te sientas preparado."
                    if spanish
                    else "I remember what you shared earlier. I'm here to keep "
                    "talking whenever you're ready."
                ),
                response_source="mock",
                reasoning_hint="summary-conditioned-response",
            )

        return LLMResult(
            reply_text=(
                "Hola, estoy aquí para escucharte. ¿De qué te gustaría hablar?"
                if spanish
                else "Hello, I'm here and ready to listen. What would you like to talk about?"
            ),
            response_source="mock",
            reasoning_hint="default-mock-response",
        )


class VllmProvider:
    provider_name = "qwen_vllm"

    async def complete(self, request: LLMRequest) -> LLMResult:
        url = f"{settings.llm_api_base}/chat/completions"

        messages = [{"role": "system", "content": request.system_prompt}]

        # 把最近上下文拼进去
        for msg in request.context_messages:
            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )

        # 当前用户输入
        user_content = request.user_text
        if request.response_language:
            user_content += f"\n\nReply entirely in {request.response_language}."
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        }

        async with httpx.AsyncClient(timeout=settings.llm_request_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        reply_text = data["choices"][0]["message"]["content"].strip()

        return LLMResult(
            reply_text=reply_text,
            response_source="qwen_vllm",
            reasoning_hint="live-vllm-response",
        )


class FallbackLLMProvider:
    provider_name = "mock-fallback"

    def __init__(self, configured_provider: str) -> None:
        self.configured_provider = configured_provider
        self._delegate = MockLLMProvider()

    async def complete(self, request: LLMRequest) -> LLMResult:
        result = await self._delegate.complete(request)
        result.response_source = f"fallback:{self.configured_provider}"
        result.reasoning_hint = "unconfigured-provider-fallback"
        return result


class LLMClient:
    def __init__(self) -> None:
        self.provider_name = settings.llm_provider
        self.model_name = settings.llm_model
        self._provider = self._build_provider()
        self._fallback = MockLLMProvider()

    def _build_provider(self) -> BaseLLMProvider:
        if settings.llm_provider == "mock":
            return MockLLMProvider()

        if settings.llm_provider in {"qwen", "qwen_vllm", "vllm"}:
            return VllmProvider()

        return FallbackLLMProvider(settings.llm_provider)

    async def generate_reply(self, request: LLMRequest) -> LLMResult:
        target_language = self._resolve_response_language(
            request.ui_language,
        )
        request.response_language = target_language
        request.system_prompt = (
            f"{request.system_prompt}\n\n"
            f"Response language: Write the entire final reply in natural "
            f"{target_language}. Do not mix languages."
        )
        try:
            result = await self._provider.complete(request)
            if not re.search(r"[\u3400-\u9fff]", result.reply_text):
                return result

            translated = await self._provider.complete(
                LLMRequest(
                    session_id=request.session_id,
                    turn_id=request.turn_id,
                    system_prompt=(
                        "Translate the following assistant response into natural, "
                        f"concise {target_language}. Preserve its meaning, empathy, "
                        "and safety advice. Output only the translated response. "
                        "Do not include Chinese characters or mix languages."
                    ),
                    user_text=result.reply_text,
                    input_mode="text",
                    context_messages=[],
                    context_summary="",
                    response_language=target_language,
                )
            )
            if re.search(r"[\u3400-\u9fff]", translated.reply_text):
                raise ValueError(
                    f"LLM {target_language} rewrite still contains Chinese text"
                )
            translated.reasoning_hint = f"rewritten-in-{target_language.lower()}"
            return translated
        except Exception:
            result = await self._fallback.complete(request)
            result.response_source = f"fallback:{self.provider_name}"
            result.reasoning_hint = "runtime-fallback-to-mock"
            return result

    def _resolve_response_language(self, ui_language: str | None = None) -> str:
        # The current interface selection is authoritative for each turn.
        if ui_language == "es":
            return "Spanish"
        if ui_language == "en":
            return "English"
        # Compatibility for clients predating the interface-language field.
        if settings.response_language in {"es", "es-es", "spanish"}:
            return "Spanish"
        return "English"


llm_client = LLMClient()
