from models import ChatRequest


class ASRClient:
    async def transcribe(self, request: ChatRequest) -> str:
        if request.user_text.strip():
            return request.user_text.strip()
        if request.audio_base64:
            return "I received your audio message."
        return ""


asr_client = ASRClient()
