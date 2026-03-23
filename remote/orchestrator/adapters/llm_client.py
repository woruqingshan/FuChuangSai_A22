from models import AvatarAction, ChatRequest


class LLMClient:
    async def generate_reply(
        self,
        request: ChatRequest,
        transcript: str,
        memory_summary: str,
        emotion_style: str,
        avatar_action: AvatarAction,
    ) -> str:
        lowered = transcript.lower()

        if any(keyword in lowered for keyword in ["sad", "unhappy", "压力", "焦虑", "难过", "不开心"]):
            return "我在这里陪着你。你可以慢慢说，我会先认真听你现在最在意的事情。"

        if request.input_type == "audio":
            return "我已经收到你的语音输入了。当前先用规则回复，下一阶段会接入 ASR 和更完整的情绪理解。"

        if memory_summary:
            return f"我记得你刚刚提到过：{memory_summary}。这次我继续陪你往下聊。"

        return "你好，我已经收到你的消息了。当前是 remote orchestrator 的规则驱动回复。"


llm_client = LLMClient()
