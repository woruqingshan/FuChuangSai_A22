import os


class Settings:
    def __init__(self) -> None:
        self.avatar_id = os.getenv("AVATAR_ID", "default-2d").strip() or "default-2d"
        self.renderer_mode = os.getenv("AVATAR_RENDERER_MODE", "parameterized_2d").strip() or "parameterized_2d"
        self.transport_mode = os.getenv("AVATAR_TRANSPORT_MODE", "http_poll").strip() or "http_poll"
        self.websocket_endpoint = os.getenv("AVATAR_WEBSOCKET_ENDPOINT", "/ws/avatar").strip() or "/ws/avatar"
        self.tmp_dir = os.getenv("TMP_DIR", "/data/zifeng/siyuan/A22/tmp/avatar").strip() or "/data/zifeng/siyuan/A22/tmp/avatar"
        self.tts_mode = os.getenv("TTS_MODE", "cosyvoice2_sft").strip().lower() or "cosyvoice2_sft"
        self.tts_model = (
            os.getenv(
                "TTS_MODEL",
                "/data/zifeng/siyuan/A22/models/CosyVoice2-0.5B",
            ).strip()
            or "/data/zifeng/siyuan/A22/models/CosyVoice2-0.5B"
        )
        self.tts_device = os.getenv("TTS_DEVICE", "cuda:0").strip() or "cuda:0"
        self.tts_repo_path = os.getenv("TTS_REPO_PATH", "").strip()
        self.tts_speaker_id = os.getenv("TTS_SPEAKER_ID", "中文女").strip() or "中文女"
        self.tts_speed = float(os.getenv("TTS_SPEED", "1.0"))
        self.tts_warmup_enabled = os.getenv("TTS_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


settings = Settings()
