import os


class Settings:
    def __init__(self) -> None:
        cloud_api_base = os.getenv("CLOUD_API_BASE", "http://127.0.0.1:19000").strip()
        self.cloud_api_base = cloud_api_base.rstrip("/")
        self.request_timeout_seconds = float(os.getenv("REMOTE_TIMEOUT_SECONDS", "15"))
        self.log_dir = os.getenv("LOG_DIR", "/logs")
        self.data_dir = os.getenv("DATA_DIR", "/data")
        self.default_session_prefix = os.getenv("DEFAULT_SESSION_PREFIX", "local-session")
        self.local_asr_provider = os.getenv("LOCAL_ASR_PROVIDER", "browser_hint").strip().lower() or "browser_hint"
        self.local_asr_model = os.getenv("LOCAL_ASR_MODEL", "small").strip() or "small"
        self.local_asr_model_path = os.getenv("LOCAL_ASR_MODEL_PATH", "").strip()
        self.local_asr_language = os.getenv("LOCAL_ASR_LANGUAGE", "zh").strip() or "zh"
        self.local_asr_device = os.getenv("LOCAL_ASR_DEVICE", "cuda:0").strip() or "cuda:0"
        self.local_asr_compute_type = os.getenv("LOCAL_ASR_COMPUTE_TYPE", "int8").strip() or "int8"
        self.local_asr_warmup_enabled = os.getenv("LOCAL_ASR_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


settings = Settings()
