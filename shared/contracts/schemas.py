from pydantic import BaseModel, Field


class AudioMetaSchema(BaseModel):
    format: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=1)
    channels: int | None = Field(default=None, ge=1)
    source: str | None = None
    frame_count: int | None = Field(default=None, ge=0)


class SpeechFeaturesSchema(BaseModel):
    transcript_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    speaking_rate: float | None = Field(default=None, ge=0.0)
    pause_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    rms_energy: float | None = Field(default=None, ge=0.0)
    peak_level: float | None = Field(default=None, ge=0.0)
    pitch_hz: float | None = Field(default=None, ge=0.0)
    dominant_channel: int | None = Field(default=None, ge=1)
    emotion_tags: list[str] = Field(default_factory=list)
    channel_rms_levels: list[float] = Field(default_factory=list)
    source: str | None = None


class VisionFeaturesSchema(BaseModel):
    scene_summary: str | None = None
    attention_target: str | None = None
    motion_level: str | None = None
    emotion_tags: list[str] = Field(default_factory=list)


class TurnTimeWindowSchema(BaseModel):
    window_id: str | None = None
    source_clock: str | None = None
    transport_mode: str | None = None
    stream_id: str | None = None
    sequence_id: int | None = Field(default=None, ge=0)
    capture_started_at_ms: int | None = Field(default=None, ge=0)
    capture_ended_at_ms: int | None = Field(default=None, ge=0)
    audio_started_at_ms: int | None = Field(default=None, ge=0)
    audio_ended_at_ms: int | None = Field(default=None, ge=0)
    video_started_at_ms: int | None = Field(default=None, ge=0)
    video_ended_at_ms: int | None = Field(default=None, ge=0)
    window_duration_ms: int | None = Field(default=None, ge=0)


class ChatRequestSchema(BaseModel):
    session_id: str = Field(..., min_length=1)
    turn_id: int = Field(..., ge=1)
    user_text: str = Field(default="")
    input_type: str = Field(default="text")
    client_ts: int | None = None
    text_source: str | None = None
    client_asr_text: str | None = None
    client_asr_source: str | None = None
    audio_base64: str | None = None
    audio_format: str | None = None
    audio_duration_ms: int | None = Field(default=None, ge=0)
    audio_sample_rate_hz: int | None = Field(default=None, ge=1)
    audio_channels: int | None = Field(default=None, ge=1)
    audio_meta: AudioMetaSchema | None = None
    speech_features: SpeechFeaturesSchema | None = None
    vision_features: VisionFeaturesSchema | None = None
    turn_time_window: TurnTimeWindowSchema | None = None
    alignment_mode: str | None = None


class AvatarActionSchema(BaseModel):
    facial_expression: str
    head_motion: str


class AvatarAudioCueSchema(BaseModel):
    audio_url: str | None = None
    mime_type: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=1)
    cache_key: str | None = None


class VisemeCueSchema(BaseModel):
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., ge=0)
    label: str = Field(..., min_length=1)
    weight: float | None = Field(default=None, ge=0.0, le=1.0)


class ExpressionCueSchema(BaseModel):
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., ge=0)
    expression: str = Field(..., min_length=1)
    intensity: float | None = Field(default=None, ge=0.0, le=1.0)


class MotionCueSchema(BaseModel):
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., ge=0)
    motion: str = Field(..., min_length=1)
    intensity: float | None = Field(default=None, ge=0.0, le=1.0)


class AvatarOutputSchema(BaseModel):
    contract_version: str = Field(default="v1")
    renderer_mode: str = Field(default="parameterized_2d")
    transport_mode: str = Field(default="http_poll")
    websocket_endpoint: str | None = None
    stream_id: str | None = None
    sequence_id: int | None = Field(default=None, ge=0)
    avatar_id: str | None = None
    emotion_style: str | None = None
    audio: AvatarAudioCueSchema | None = None
    viseme_seq: list[VisemeCueSchema] = Field(default_factory=list)
    expression_seq: list[ExpressionCueSchema] = Field(default_factory=list)
    motion_seq: list[MotionCueSchema] = Field(default_factory=list)


class ChatResponseSchema(BaseModel):
    server_status: str
    reply_text: str
    emotion_style: str
    avatar_action: AvatarActionSchema
    avatar_output: AvatarOutputSchema | None = None
    server_ts: int | None = None
    input_mode: str | None = None
    response_source: str | None = None
    context_summary: str | None = None
    reasoning_hint: str | None = None
    turn_time_window: TurnTimeWindowSchema | None = None
    alignment_mode: str | None = None


class ErrorResponseSchema(BaseModel):
    detail: str
