import os


class Settings:
    def __init__(self) -> None:
        cloud_api_base = os.getenv("CLOUD_API_BASE", "http://127.0.0.1:19000").strip()
        self.cloud_api_base = cloud_api_base.rstrip("/")
        self.remote_transport = os.getenv("REMOTE_TRANSPORT", "http").strip().lower() or "http"
        cloud_ws_chat_endpoint = os.getenv("CLOUD_WS_CHAT_ENDPOINT", "").strip()
        self.cloud_ws_chat_endpoint = cloud_ws_chat_endpoint or self._default_ws_chat_endpoint(self.cloud_api_base)
        self.request_timeout_seconds = float(os.getenv("REMOTE_TIMEOUT_SECONDS", "15"))
        self.status_timeout_seconds = float(os.getenv("STATUS_TIMEOUT_SECONDS", "2.5"))
        self.media_connect_timeout_seconds = float(os.getenv("MEDIA_CONNECT_TIMEOUT_SECONDS", "5"))
        self.media_manifest_timeout_seconds = float(os.getenv("MEDIA_MANIFEST_TIMEOUT_SECONDS", "5"))
        self.media_read_timeout_seconds = float(os.getenv("MEDIA_READ_TIMEOUT_SECONDS", "300"))
        self.session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "a22_session").strip() or "a22_session"
        self.session_ttl_seconds = max(60, int(os.getenv("SESSION_TTL_SECONDS", "86400")))
        self.session_cookie_secure = self._parse_bool(os.getenv("SESSION_COOKIE_SECURE", "true"))
        self.session_cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower() or "lax"
        self.log_dir = os.getenv("LOG_DIR", "/logs")
        self.data_dir = os.getenv("DATA_DIR", "/data")
        self.default_session_prefix = os.getenv("DEFAULT_SESSION_PREFIX", "local-session")
        self.audio_pipeline_role = (
            os.getenv("AUDIO_PIPELINE_ROLE", "remote_forward_only").strip().lower() or "remote_forward_only"
        )
        self.local_video_frame_limit = max(1, int(os.getenv("LOCAL_VIDEO_FRAME_LIMIT", "3")))
        self.local_video_max_dimension = max(64, int(os.getenv("LOCAL_VIDEO_MAX_DIMENSION", "640")))

    @staticmethod
    def _default_ws_chat_endpoint(cloud_api_base: str) -> str:
        if cloud_api_base.startswith("https://"):
            return f"wss://{cloud_api_base[len('https://'):]}/ws/chat"
        if cloud_api_base.startswith("http://"):
            return f"ws://{cloud_api_base[len('http://'):]}/ws/chat"
        return ""

    @staticmethod
    def _parse_bool(raw_value: str | None) -> bool:
        return str(raw_value or "").strip().lower() not in {"0", "false", "no", "off"}


settings = Settings()
