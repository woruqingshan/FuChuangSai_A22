from models import AvatarAction, ChatRequest


class PolicyService:
    def select_emotion_style(self, request: ChatRequest, transcript: str) -> str:
        lowered = transcript.lower()
        if request.input_type == "audio":
            return "listening"
        if any(keyword in lowered for keyword in ["sad", "unhappy", "压力", "焦虑", "难过", "不开心"]):
            return "gentle"
        return "supportive"

    def select_avatar_action(self, request: ChatRequest, transcript: str) -> AvatarAction:
        lowered = transcript.lower()
        if request.input_type == "audio":
            return AvatarAction(
                facial_expression="attentive",
                head_motion="slow_nod",
            )
        if any(keyword in lowered for keyword in ["sad", "unhappy", "压力", "焦虑", "难过", "不开心"]):
            return AvatarAction(
                facial_expression="soft_concern",
                head_motion="slow_nod",
            )
        return AvatarAction(
            facial_expression="neutral_smile",
            head_motion="steady",
        )


policy_service = PolicyService()
