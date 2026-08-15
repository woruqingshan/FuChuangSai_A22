from models import AvatarAction, ChatRequest


CONCERN_KEYWORDS = (
    "sad",
    "unhappy",
    "anxious",
    "anxiety",
    "worried",
    "worry",
    "stress",
    "pressure",
    "\u538b\u529b",
    "\u7126\u8651",
    "\u62c5\u5fc3",
    "\u62c5\u5fe7",
    "\u5bb3\u6015",
    "\u96be\u8fc7",
    "\u60b2\u4f24",
    "\u4e0d\u5f00\u5fc3",
)


def _contains_concern(text: str) -> bool:
    return any(keyword in text for keyword in CONCERN_KEYWORDS)


class PolicyService:
    def select_emotion_style(self, request: ChatRequest, transcript: str) -> str:
        lowered = transcript.lower()
        speech_tags = {tag.lower() for tag in (request.speech_features.emotion_tags if request.speech_features else [])}
        if request.input_type == "audio" and {"hesitant", "fatigued", "agitated"} & speech_tags:
            return "gentle"
        if request.input_type == "audio" and "energized" in speech_tags:
            return "attentive"
        if request.input_type == "audio":
            return "listening"
        if _contains_concern(lowered):
            return "gentle"
        return "supportive"

    def select_avatar_action(self, request: ChatRequest, transcript: str) -> AvatarAction:
        lowered = transcript.lower()
        speech_tags = {tag.lower() for tag in (request.speech_features.emotion_tags if request.speech_features else [])}
        if request.input_type == "audio" and {"hesitant", "fatigued"} & speech_tags:
            return AvatarAction(
                facial_expression="soft_concern",
                head_motion="slow_nod",
            )
        if request.input_type == "audio" and "energized" in speech_tags:
            return AvatarAction(
                facial_expression="attentive",
                head_motion="steady",
            )
        if request.input_type == "audio":
            return AvatarAction(
                facial_expression="attentive",
                head_motion="slow_nod",
            )
        if _contains_concern(lowered):
            return AvatarAction(
                facial_expression="soft_concern",
                head_motion="slow_nod",
            )
        return AvatarAction(
            facial_expression="neutral_smile",
            head_motion="steady",
        )


policy_service = PolicyService()
