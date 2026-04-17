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
        self.ser_enabled = os.getenv("SER_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.ser_provider = os.getenv("SER_PROVIDER", "emotion2vec_plus_base").strip().lower() or "emotion2vec_plus_base"
        self.ser_model = (
            os.getenv(
                "SER_MODEL",
                "/data/zifeng/siyuan/A22/models/emotion2vec_plus_base",
            ).strip()
            or "/data/zifeng/siyuan/A22/models/emotion2vec_plus_base"
        )
        self.ser_device = os.getenv("SER_DEVICE", self.asr_device).strip() or self.asr_device
        self.ser_hub = os.getenv("SER_HUB", "ms").strip().lower() or "ms"
        self.ser_top_k = max(1, int(os.getenv("SER_TOP_K", "3")))
        self.ser_min_confidence = min(max(float(os.getenv("SER_MIN_CONFIDENCE", "0.2")), 0.0), 1.0)
        self.ser_warmup_enabled = os.getenv("SER_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.qwen_asr_use_flash_attn = os.getenv("QWEN_ASR_USE_FLASH_ATTN", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.qwen_asr_use_itn = os.getenv("QWEN_ASR_USE_ITN", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.tmp_dir = os.getenv("TMP_DIR", "/data/zifeng/siyuan/A22/tmp/speech").strip() or "/data/zifeng/siyuan/A22/tmp/speech"


settings = Settings()
