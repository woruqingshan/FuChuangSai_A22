from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    turn_id: int = Field(..., ge=1)
    user_text: str = Field(default="")
    input_type: str = Field(default="text")
    client_ts: int | None = None
    audio_base64: str | None = None
    audio_format: str | None = None
    audio_duration_ms: int | None = Field(default=None, ge=0)


class AvatarAction(BaseModel):
    facial_expression: str
    head_motion: str


class ChatResponse(BaseModel):
    server_status: str
    reply_text: str
    emotion_style: str
    avatar_action: AvatarAction
    server_ts: int | None = None
    input_mode: str | None = None
    reply_audio_url: str | None = None


class HealthResponse(BaseModel):
    status: str
    server_time: str
    orchestrator_mode: str


class ErrorResponse(BaseModel):
    detail: str
