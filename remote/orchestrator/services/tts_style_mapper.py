from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TTSStylePreset:
    instruct_text: str
    speed: float
    speaker_id: str | None = None


@dataclass(frozen=True)
class TTSRenderPlan:
    emotion_style: str
    tts_instruct_text: str
    tts_speed: float
    tts_speaker_id: str | None = None

    def to_avatar_payload(self) -> dict:
        return {
            "emotion_style": self.emotion_style,
            "tts_instruct_text": self.tts_instruct_text,
            "tts_speed": self.tts_speed,
            "tts_speaker_id": self.tts_speaker_id,
        }

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_TTS_STYLE_PRESETS: dict[str, TTSStylePreset] = {
    "gentle": TTSStylePreset(
        instruct_text=(
            "请用温柔、低刺激、带安抚感的女声朗读，语速明显放慢，"
            "句间停顿更充分，像在耐心安慰情绪低落的人。<|endofprompt|>"
        ),
        speed=0.82,
        speaker_id="中文女",
    ),
    "supportive": TTSStylePreset(
        instruct_text=(
            "请用温暖、真诚、带陪伴感的女声朗读，语气轻柔但有力量，"
            "让人感到被支持和鼓励。<|endofprompt|>"
        ),
        speed=0.95,
        speaker_id="中文女",
    ),
    "neutral": TTSStylePreset(
        instruct_text=(
            "请用平静、自然、标准普通话女声朗读，保持正常语速，"
            "语气客观中性，不加入明显情绪色彩。<|endofprompt|>"
        ),
        speed=1.0,
        speaker_id="中文女",
    ),
    "attentive": TTSStylePreset(
        instruct_text=(
            "请用认真、专注、带关切感但不过分夸张的女声朗读，"
            "语速略慢，表达出稳定和耐心。<|endofprompt|>"
        ),
        speed=0.93,
        speaker_id="中文女",
    ),
    "listening": TTSStylePreset(
        instruct_text=(
            "请用轻柔、耐心、认真倾听的女声朗读，语速略慢，"
            "停顿自然，表达出专注陪伴感。<|endofprompt|>"
        ),
        speed=0.9,
        speaker_id="中文女",
    ),
    "encouraging": TTSStylePreset(
        instruct_text=(
            "请用积极、明亮、真诚的女声朗读，语速略快，"
            "整体情绪向上但不要显得夸张。<|endofprompt|>"
        ),
        speed=1.05,
        speaker_id="中文女",
    ),
}


class TTSStyleMapper:
    def __init__(
        self,
        presets: dict[str, TTSStylePreset] | None = None,
        *,
        default_style: str = "supportive",
    ) -> None:
        self._presets = presets or DEFAULT_TTS_STYLE_PRESETS
        self._default_style = default_style

    def build_plan(
        self,
        *,
        emotion_style: str | None,
        reply_text: str,
        override_instruct_text: str | None = None,
        override_speed: float | None = None,
        override_speaker_id: str | None = None,
    ) -> TTSRenderPlan:
        resolved_style = self._resolve_style(emotion_style)
        preset = self._presets[resolved_style]

        instruct_text = self._resolve_instruct_text(
            override_instruct_text=override_instruct_text,
            preset=preset,
            reply_text=reply_text,
        )
        speed = override_speed if override_speed is not None else preset.speed
        speaker_id = override_speaker_id if override_speaker_id is not None else preset.speaker_id

        return TTSRenderPlan(
            emotion_style=resolved_style,
            tts_instruct_text=instruct_text,
            tts_speed=speed,
            tts_speaker_id=speaker_id,
        )

    def _resolve_style(self, emotion_style: str | None) -> str:
        normalized = (emotion_style or "").strip().lower()
        if normalized in self._presets:
            return normalized
        return self._default_style

    def _resolve_instruct_text(
        self,
        *,
        override_instruct_text: str | None,
        preset: TTSStylePreset,
        reply_text: str,
    ) -> str:
        instruct_text = (override_instruct_text or "").strip()
        if instruct_text:
            if "<|endofprompt|>" not in instruct_text:
                return f"{instruct_text}<|endofprompt|>"
            return instruct_text

        # Keep a defensive default so the mapper remains usable even if the
        # preset table is accidentally trimmed in later iterations.
        if preset.instruct_text.strip():
            return preset.instruct_text

        return (
            "请用自然、清晰、标准普通话女声朗读以下内容，"
            f"保持语义完整：{reply_text[:120]}<|endofprompt|>"
        )


tts_style_mapper = TTSStyleMapper()
