import os


class Settings:
    def __init__(self) -> None:
        self.asr_provider = os.getenv("ASR_PROVIDER", "belle_whisper").strip().lower() or "belle_whisper"
        self.asr_model = (
            os.getenv(
                "ASR_MODEL",
                "/data/zifeng/siyuan/A22/models/Belle-whisper-large-v3-turbo-zh",
            ).strip()
            or "/data/zifeng/siyuan/A22/models/Belle-whisper-large-v3-turbo-zh"
        )
        self.asr_language = os.getenv("ASR_LANGUAGE", "zh").strip() or "zh"
        self.asr_device = os.getenv("ASR_DEVICE", "cuda:0").strip() or "cuda:0"
        self.asr_warmup_enabled = os.getenv("ASR_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.tmp_dir = os.getenv("TMP_DIR", "/data/zifeng/siyuan/A22/tmp/speech").strip() or "/data/zifeng/siyuan/A22/tmp/speech"


settings = Settings()
