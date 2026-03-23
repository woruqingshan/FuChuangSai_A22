from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None)
    turn_id: int | None = Field(default=None, ge=1)
    user_text: str | None = Field(default=None)
    input_type: str = Field(default="text")
    client_ts: int | None = None
    audio_base64: str | None = None
    audio_format: str | None = None
    audio_duration_ms: int | None = Field(default=None, ge=0)


class RemoteChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    turn_id: int = Field(..., ge=1)
    user_text: str = Field(..., min_length=1)
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


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    cloud_api_base: str
    request_timeout_seconds: float
