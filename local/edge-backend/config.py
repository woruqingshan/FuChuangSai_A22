import os


class Settings:
    def __init__(self) -> None:
        cloud_api_base = os.getenv("CLOUD_API_BASE", "http://127.0.0.1:19000").strip()
        self.cloud_api_base = cloud_api_base.rstrip("/")
        self.request_timeout_seconds = float(os.getenv("REMOTE_TIMEOUT_SECONDS", "15"))
        self.log_dir = os.getenv("LOG_DIR", "/logs")
        self.data_dir = os.getenv("DATA_DIR", "/data")
        self.default_session_prefix = os.getenv("DEFAULT_SESSION_PREFIX", "local-session")


settings = Settings()
