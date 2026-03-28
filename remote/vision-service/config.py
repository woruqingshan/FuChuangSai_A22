import os


class Settings:
    def __init__(self) -> None:
        self.tmp_dir = os.getenv("TMP_DIR", "/data/zifeng/siyuan/A22/tmp/vision").strip() or "/data/zifeng/siyuan/A22/tmp/vision"
        self.extractor_mode = os.getenv("VISION_EXTRACTOR_MODE", "qwen2_5_vl").strip().lower() or "qwen2_5_vl"
        self.vision_model = (
            os.getenv(
                "VISION_MODEL",
                "/data/zifeng/siyuan/A22/models/Qwen2.5-VL-7B-Instruct",
            ).strip()
            or "/data/zifeng/siyuan/A22/models/Qwen2.5-VL-7B-Instruct"
        )
        self.vision_device = os.getenv("VISION_DEVICE", "cuda:0").strip() or "cuda:0"
        self.frame_input_mode = os.getenv("VISION_FRAME_INPUT_MODE", "event_window_keyframes").strip().lower() or "event_window_keyframes"
        self.vision_dtype = os.getenv("VISION_DTYPE", "float16").strip().lower() or "float16"
        self.vision_max_new_tokens = max(32, int(os.getenv("VISION_MAX_NEW_TOKENS", "192")))
        self.vision_warmup_enabled = os.getenv("VISION_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


settings = Settings()
