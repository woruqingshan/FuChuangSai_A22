import os
from pathlib import Path


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


class Settings:
    def __init__(self) -> None:
        self.avatar_id = _env_str("AVATAR_ID", "default-2d") or "default-2d"
        self.renderer_mode = _env_str("AVATAR_RENDERER_MODE", "parameterized_2d") or "parameterized_2d"
        self.transport_mode = _env_str("AVATAR_TRANSPORT_MODE", "http_poll") or "http_poll"
        self.websocket_endpoint = _env_str("AVATAR_WEBSOCKET_ENDPOINT", "/ws/avatar") or "/ws/avatar"
        self.tmp_dir = _env_str("TMP_DIR", "/root/autodl-tmp/a22/tmp/avatar") or "/root/autodl-tmp/a22/tmp/avatar"
        self.avatar_renderer_backend = (
            _env_str("AVATAR_RENDERER_BACKEND", "echomimic_v2").lower() or "echomimic_v2"
        )
        self.echomimic_root = _env_str("ECHOMIMIC_ROOT", "")
        self.echomimic_infer_script = _env_str("ECHOMIMIC_INFER_SCRIPT", "infer_acc.py") or "infer_acc.py"
        self.echomimic_ref_image_path = _env_str("ECHOMIMIC_REF_IMAGE_PATH", "")
        self.echomimic_pose_dir = _env_str("ECHOMIMIC_POSE_DIR", "")
        self.echomimic_timeout_seconds = float(_env_str("ECHOMIMIC_TIMEOUT_SECONDS", "1800"))
        self.echomimic_v3_root = _env_str("ECHOMIMIC_V3_ROOT", "/root/autodl-tmp/a22/code/echomimic_v3")
        self.echomimic_v3_python = _env_str(
            "ECHOMIMIC_V3_PYTHON", "/root/autodl-tmp/a22/.uv_envs/echomimic-v3/bin/python"
        )
        self.echomimic_v3_infer_script = _env_str("ECHOMIMIC_V3_INFER_SCRIPT", "infer_flash.py")
        self.echomimic_v3_config_path = _env_str("ECHOMIMIC_V3_CONFIG_PATH", "config/config.yaml")
        self.echomimic_v3_model_path = _env_str(
            "ECHOMIMIC_V3_MODEL_PATH",
            "/root/autodl-tmp/a22/models/echomimic_v3_flash/Wan2.1-Fun-V1.1-1.3B-InP",
        )
        self.echomimic_v3_transformer_path = _env_str(
            "ECHOMIMIC_V3_TRANSFORMER_PATH",
            "/root/autodl-tmp/a22/models/echomimic_v3_flash/flash/transformer/diffusion_pytorch_model.safetensors",
        )
        self.echomimic_v3_wav2vec_path = _env_str(
            "ECHOMIMIC_V3_WAV2VEC_PATH",
            "/root/autodl-tmp/a22/models/echomimic_v3_flash/flash/chinese-wav2vec2-base",
        )
        self.echomimic_v3_ref_image_path = _env_str("ECHOMIMIC_V3_REF_IMAGE_PATH", "")
        self.echomimic_v3_timeout_seconds = float(_env_str("ECHOMIMIC_V3_TIMEOUT_SECONDS", "3600"))
        self.echomimic_v3_width = int(_env_str("ECHOMIMIC_V3_WIDTH", "768"))
        self.echomimic_v3_height = int(_env_str("ECHOMIMIC_V3_HEIGHT", "768"))
        self.echomimic_v3_fps = int(_env_str("ECHOMIMIC_V3_FPS", "25"))
        self.echomimic_v3_steps = int(_env_str("ECHOMIMIC_V3_STEPS", "8"))
        self.echomimic_v3_max_frames = int(_env_str("ECHOMIMIC_V3_MAX_FRAMES", "201"))
        self.echomimic_v3_guidance_scale = float(_env_str("ECHOMIMIC_V3_GUIDANCE_SCALE", "6.0"))
        self.echomimic_v3_audio_guidance_scale = float(
            _env_str("ECHOMIMIC_V3_AUDIO_GUIDANCE_SCALE", "3.0")
        )
        self.echomimic_v3_seed = int(_env_str("ECHOMIMIC_V3_SEED", "43"))
        self.echomimic_v3_gpu_memory_mode = _env_str(
            "ECHOMIMIC_V3_GPU_MEMORY_MODE", "sequential_cpu_offload"
        )
        self.echomimic_v3_weight_dtype = _env_str("ECHOMIMIC_V3_WEIGHT_DTYPE", "bfloat16")
        self.echomimic_v3_teacache_threshold = float(
            _env_str("ECHOMIMIC_V3_TEACACHE_THRESHOLD", "0.1")
        )
        self.echomimic_v3_prompt_template = _env_str(
            "ECHOMIMIC_V3_PROMPT_TEMPLATE",
            "A Chinese female digital human is speaking naturally. She appears {emotion_prompt}, "
            "showing {expression_prompt}, with {motion_prompt}. Natural upper-body gestures, "
            "stable identity, realistic facial details.",
        )
        self.echomimic_v3_negative_prompt = _env_str(
            "ECHOMIMIC_V3_NEGATIVE_PROMPT",
            "Deformed face, frozen expression, bad lip sync, exaggerated movement, bad hands, "
            "fused fingers, twisted fingers, blurry hands, identity drift.",
        )
        self.soulx_root = _env_str("SOULX_ROOT", "")
        self.soulx_infer_script = _env_str("SOULX_INFER_SCRIPT", "infer_stream.py") or "infer_stream.py"
        self.soulx_ref_image_path = _env_str("SOULX_REF_IMAGE_PATH", "")
        self.soulx_timeout_seconds = float(_env_str("SOULX_TIMEOUT_SECONDS", "1200"))
        self.soulx_chunk_seconds = float(_env_str("SOULX_CHUNK_SECONDS", "2.0"))
        self.soulx_fps = int(_env_str("SOULX_FPS", "25"))
        self.soulx_async_render = _env_str("SOULX_ASYNC_RENDER", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.soulx_command_template = _env_str("SOULX_COMMAND_TEMPLATE", "")
        self.soulx_extra_args = _env_str("SOULX_EXTRA_ARGS", "")

        self.tts_mode = _env_str("TTS_MODE", "cosyvoice2_sft").lower() or "cosyvoice2_sft"
        self.tts_model = (
            _env_str("TTS_MODEL", "/root/autodl-tmp/a22/models/CosyVoice2-0.5B")
            or "/root/autodl-tmp/a22/models/CosyVoice2-0.5B"
        )
        self.tts_device = _env_str("TTS_DEVICE", "cuda:0") or "cuda:0"
        self.tts_repo_path = _env_str("TTS_REPO_PATH", "/root/autodl-tmp/a22/models/CosyVoice")
        # Use a fixed default speaker to keep timbre stable across turns.
        self.tts_speaker_id = _env_str("TTS_SPEAKER_ID", "中文女")
        self.tts_prompt_wav = _env_str("TTS_PROMPT_WAV", "")
        self.tts_prompt_text = _env_str("TTS_PROMPT_TEXT", "YOUR_PROMPT_TEXT|endofprompt|>")
        self.tts_instruct_text = _env_str("TTS_INSTRUCT_TEXT", "YOUR_INSTRUCT_TEXT|endofprompt|>")
        self.tts_speed = float(_env_str("TTS_SPEED", "1.0"))
        self.tts_warmup_enabled = _env_str("TTS_WARMUP_ENABLED", "true").lower() in {
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
