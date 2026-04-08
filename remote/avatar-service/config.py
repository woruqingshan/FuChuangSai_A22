import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.avatar_id = os.getenv("AVATAR_ID", "default-2d").strip() or "default-2d"
        self.renderer_mode = os.getenv("AVATAR_RENDERER_MODE", "parameterized_2d").strip() or "parameterized_2d"
        self.transport_mode = os.getenv("AVATAR_TRANSPORT_MODE", "http_poll").strip() or "http_poll"
        self.websocket_endpoint = os.getenv("AVATAR_WEBSOCKET_ENDPOINT", "/ws/avatar").strip() or "/ws/avatar"
        self.tmp_dir = os.getenv("TMP_DIR", "/data/zifeng/siyuan/A22/tmp/avatar").strip() or "/data/zifeng/siyuan/A22/tmp/avatar"
        self.avatar_renderer_backend = (
            os.getenv("AVATAR_RENDERER_BACKEND", "echomimic_v2").strip().lower() or "echomimic_v2"
        )
        self.echomimic_root = os.getenv("ECHOMIMIC_ROOT", "").strip()
        self.echomimic_infer_script = os.getenv("ECHOMIMIC_INFER_SCRIPT", "infer_acc.py").strip() or "infer_acc.py"
        self.echomimic_ref_image_path = os.getenv("ECHOMIMIC_REF_IMAGE_PATH", "").strip()
        self.echomimic_pose_dir = os.getenv("ECHOMIMIC_POSE_DIR", "").strip()
        self.echomimic_timeout_seconds = float(os.getenv("ECHOMIMIC_TIMEOUT_SECONDS", "1800"))
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
        self.tts_prompt_wav = os.getenv("TTS_PROMPT_WAV", "").strip()
        self.tts_prompt_text = (
            os.getenv("TTS_PROMPT_TEXT", "以下是一段中文语音提示。<|endofprompt|>").strip()
            or "以下是一段中文语音提示。<|endofprompt|>"
        )
        self.tts_instruct_text = (
            os.getenv("TTS_INSTRUCT_TEXT", "请用标准普通话女声自然朗读。<|endofprompt|>").strip()
            or "请用标准普通话女声自然朗读。<|endofprompt|>"
        )
        self.tts_speed = float(os.getenv("TTS_SPEED", "1.0"))
        self.tts_warmup_enabled = os.getenv("TTS_WARMUP_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @property
    def tts_prompt_wav_path(self) -> str:
        if self.tts_prompt_wav:
            return self.tts_prompt_wav

        repo = Path(self.tts_repo_path).expanduser() if self.tts_repo_path else None
        if repo:
            candidate = repo / "asset" / "zero_shot_prompt.wav"
            if candidate.exists():
                return str(candidate)
        return ""


settings = Settings()
