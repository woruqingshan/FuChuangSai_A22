from dataclasses import asdict, dataclass, field
from pathlib import Path
import subprocess


EMOTION_PROMPTS = {
    "supportive": "warm, empathetic and reassuring, with a gentle smile and attentive eyes",
    "gentle": "calm and gentle, with a soft expression and restrained movement",
    "encouraging": "positive and encouraging, with a warm smile and confident open gestures",
    "cheerful": "cheerful and lively, with a bright natural smile and expressive eyes",
    "concerned": "concerned and attentive, with slightly furrowed brows and a caring gaze",
    "sad": "subdued and sad, with restrained facial movement and a downcast gaze",
    "neutral": "natural and composed, with a neutral attentive expression",
}

EXPRESSION_PROMPTS = {
    "smile": "a natural smile",
    "gentle_smile": "a gentle reassuring smile",
    "happy": "a bright but natural smile",
    "concerned": "slightly furrowed brows and an attentive gaze",
    "sad": "a subtle sad expression",
    "neutral": "a composed neutral expression",
}

MOTION_PROMPTS = {
    "nod": "occasional natural nods",
    "slow_nod": "subtle slow reassuring nods",
    "tilt": "a slight natural head tilt",
    "steady": "restrained head and upper-body movement",
    "open_palms": "natural open-hand gestures",
    "hand_on_chest": "an occasional gentle hand-to-chest gesture",
}


@dataclass(frozen=True)
class EchoMimicV3RenderRequest:
    session_id: str
    turn_id: int
    audio_path: str
    ref_image_path: str
    prompt: str
    negative_prompt: str
    width: int = 768
    height: int = 768
    fps: int = 25
    video_length: int = 81
    steps: int = 8
    guidance_scale: float = 6.0
    audio_guidance_scale: float = 3.0
    seed: int = 43
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EchoMimicV3RenderResult:
    video_path: str
    audio_path: str
    ref_image_path: str
    renderer: str = "echomimic_v3_flash_pro"
    fps: int | None = None
    frame_count: int | None = None
    duration_ms: int | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EchoMimicV3RenderBridge:
    def build_prompt(
        self,
        *,
        emotion_style: str | None,
        facial_expression: str | None,
        head_motion: str | None,
        prompt_template: str,
    ) -> str:
        emotion_key = self._normalize_key(emotion_style, "supportive")
        expression_key = self._normalize_key(facial_expression, "neutral")
        motion_key = self._normalize_key(head_motion, "steady")
        values = {
            "emotion_style": emotion_key,
            "emotion_prompt": EMOTION_PROMPTS.get(emotion_key, EMOTION_PROMPTS["supportive"]),
            "facial_expression": expression_key,
            "expression_prompt": EXPRESSION_PROMPTS.get(expression_key, expression_key.replace("_", " ")),
            "head_motion": motion_key,
            "motion_prompt": MOTION_PROMPTS.get(motion_key, motion_key.replace("_", " ")),
        }
        rendered = prompt_template
        for key, value in values.items():
            rendered = rendered.replace(f"{{{key}}}", value)
        return " ".join(rendered.split())

    def build_request(
        self,
        *,
        session_id: str,
        turn_id: int,
        audio_path: str,
        ref_image_path: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        fps: int,
        video_length: int,
        steps: int,
        guidance_scale: float,
        audio_guidance_scale: float,
        seed: int,
        metadata: dict | None = None,
    ) -> EchoMimicV3RenderRequest:
        return EchoMimicV3RenderRequest(
            session_id=session_id,
            turn_id=turn_id,
            audio_path=audio_path,
            ref_image_path=ref_image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=max(int(width), 64),
            height=max(int(height), 64),
            fps=max(int(fps), 1),
            video_length=self.align_video_length(video_length),
            steps=max(int(steps), 1),
            guidance_scale=max(float(guidance_scale), 0.0),
            audio_guidance_scale=max(float(audio_guidance_scale), 0.0),
            seed=int(seed),
            metadata=metadata or {},
        )

    @staticmethod
    def align_video_length(frame_count: int) -> int:
        # Wan VAE uses temporal compression ratio 4 and requires 4n+1 frames.
        requested = max(int(frame_count), 1)
        return ((requested - 1) // 4) * 4 + 1

    def build_cli_args(
        self,
        request: EchoMimicV3RenderRequest,
        *,
        python_path: str,
        infer_script: str,
        config_path: str,
        model_path: str,
        transformer_path: str,
        wav2vec_path: str,
        output_dir: str,
        gpu_memory_mode: str,
        weight_dtype: str,
        teacache_threshold: float,
    ) -> list[str]:
        return [
            python_path,
            infer_script,
            "--image_path", request.ref_image_path,
            "--audio_path", request.audio_path,
            "--prompt", request.prompt,
            "--negative_prompt", request.negative_prompt,
            "--num_inference_steps", str(request.steps),
            "--config_path", config_path,
            "--model_name", model_path,
            "--transformer_path", transformer_path,
            "--save_path", output_dir,
            "--wav2vec_model_dir", wav2vec_path,
            "--sampler_name", "Flow_Unipc",
            "--video_length", str(request.video_length),
            "--guidance_scale", str(request.guidance_scale),
            "--audio_guidance_scale", str(request.audio_guidance_scale),
            "--seed", str(request.seed),
            "--enable_teacache",
            "--teacache_threshold", str(teacache_threshold),
            "--num_skip_start_steps", "5",
            "--GPU_memory_mode", gpu_memory_mode,
            "--weight_dtype", weight_dtype,
            "--sample_size", str(request.width), str(request.height),
            "--fps", str(request.fps),
            "--shift", "5.0",
        ]

    def render_video(
        self,
        request: EchoMimicV3RenderRequest,
        *,
        workdir: str,
        python_path: str,
        infer_script: str,
        config_path: str,
        model_path: str,
        transformer_path: str,
        wav2vec_path: str,
        timeout_seconds: float,
        gpu_memory_mode: str,
        weight_dtype: str,
        teacache_threshold: float,
    ) -> EchoMimicV3RenderResult:
        workdir_path = Path(workdir).expanduser().resolve()
        self._require_file(Path(python_path), "EchoMimicV3 Python")
        self._require_file(workdir_path / infer_script, "EchoMimicV3 inference script")
        self._require_file(Path(request.audio_path), "audio input")
        self._require_file(Path(request.ref_image_path), "reference image")
        self._require_file(Path(transformer_path), "EchoMimicV3 transformer")
        self._require_dir(Path(model_path), "EchoMimicV3 base model")
        self._require_dir(Path(wav2vec_path), "EchoMimicV3 wav2vec model")

        output_dir = workdir_path / "outputs" / "avatar-service" / request.session_id / str(request.turn_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        cli_args = self.build_cli_args(
            request,
            python_path=python_path,
            infer_script=infer_script,
            config_path=config_path,
            model_path=model_path,
            transformer_path=transformer_path,
            wav2vec_path=wav2vec_path,
            output_dir=str(output_dir),
            gpu_memory_mode=gpu_memory_mode,
            weight_dtype=weight_dtype,
            teacache_threshold=teacache_threshold,
        )
        completed = subprocess.run(
            cli_args,
            cwd=str(workdir_path),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "EchoMimicV3 render failed. "
                f"exit_code={completed.returncode}; "
                f"stdout={completed.stdout[-1600:]}; stderr={completed.stderr[-1600:]}"
            )

        expected_path = output_dir / f"{Path(request.ref_image_path).stem}_output.mp4"
        if not expected_path.is_file():
            raise RuntimeError(f"EchoMimicV3 render finished but output was not found: {expected_path}")
        return EchoMimicV3RenderResult(
            video_path=str(expected_path),
            audio_path=request.audio_path,
            ref_image_path=request.ref_image_path,
            fps=request.fps,
            frame_count=request.video_length,
            duration_ms=round(request.video_length / request.fps * 1000),
            metadata={"prompt": request.prompt, **request.metadata},
        )

    @staticmethod
    def _normalize_key(value: str | None, default: str) -> str:
        return (value or default).strip().lower().replace("-", "_") or default

    @staticmethod
    def _require_file(path: Path, label: str) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"{label} does not exist: {path}")

    @staticmethod
    def _require_dir(path: Path, label: str) -> None:
        if not path.is_dir():
            raise FileNotFoundError(f"{label} does not exist: {path}")


echomimic_v3_render_bridge = EchoMimicV3RenderBridge()
