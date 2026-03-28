from models import AvatarAction, AvatarOutput, ChatRequest


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
        if any(keyword in lowered for keyword in ["sad", "unhappy", "压力", "焦虑", "难过", "不开心"]):
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
        if any(keyword in lowered for keyword in ["sad", "unhappy", "压力", "焦虑", "难过", "不开心"]):
            return AvatarAction(
                facial_expression="soft_concern",
                head_motion="slow_nod",
            )
        return AvatarAction(
            facial_expression="neutral_smile",
            head_motion="steady",
        )

    def build_avatar_output(
        self,
        *,
        request: ChatRequest,
        emotion_style: str,
        avatar_action: AvatarAction,
        reply_text: str,
        reply_audio_url: str | None,
    ) -> AvatarOutput:
        estimated_duration_ms = min(max(len(reply_text) * 180, 1200), 8000)

        return AvatarOutput(
            contract_version="v1",
            renderer_mode="parameterized_2d",
            transport_mode="http_poll",
            websocket_endpoint="/ws/avatar",
            stream_id=request.turn_time_window.stream_id if request.turn_time_window else None,
            sequence_id=request.turn_id,
            avatar_id="default-2d",
            emotion_style=emotion_style,
            audio={
                "audio_url": reply_audio_url,
                "mime_type": "audio/wav" if reply_audio_url else None,
                "duration_ms": estimated_duration_ms if reply_audio_url else None,
                "cache_key": f"{request.session_id}:{request.turn_id}:tts" if reply_audio_url else None,
            },
            viseme_seq=[
                {
                    "start_ms": 0,
                    "end_ms": estimated_duration_ms // 3,
                    "label": "viseme_open",
                    "weight": 0.55,
                },
                {
                    "start_ms": estimated_duration_ms // 3,
                    "end_ms": (estimated_duration_ms * 2) // 3,
                    "label": "viseme_mid",
                    "weight": 0.5,
                },
                {
                    "start_ms": (estimated_duration_ms * 2) // 3,
                    "end_ms": estimated_duration_ms,
                    "label": "viseme_closed",
                    "weight": 0.45,
                },
            ],
            expression_seq=[
                {
                    "start_ms": 0,
                    "end_ms": estimated_duration_ms,
                    "expression": avatar_action.facial_expression,
                    "intensity": 0.72,
                }
            ],
            motion_seq=[
                {
                    "start_ms": 0,
                    "end_ms": estimated_duration_ms,
                    "motion": avatar_action.head_motion,
                    "intensity": 0.6,
                }
            ],
        )


policy_service = PolicyService()
