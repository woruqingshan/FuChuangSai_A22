from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import subprocess


@dataclass(frozen=True)
class LiveAvatarRenderRequest:
    session_id: st
    turn_id: int
    audio_path: st
    ref_image_path: st
    prompt: st
    num_clip: int = 10000
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LiveAvatarRenderResult:
    video_path: st
    audio_path: st
    ref_image_path: st
    renderer: str = "liveavatar"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class LiveAvatarRenderBridge:
    def build_request(
        self,
        *,
        session_id: str,
        turn_id: int,
        audio_path: str,
        ref_image_path: str,
        emotion_style: str,
        facial_expression: str,
        head_motion: str,
        prompt_template: str,
        num_clip: int,
        metadata: dict | None = None,
    ) -> LiveAvatarRenderRequest:
        prompt = self.build_prompt(
            emotion_style=emotion_style,
            facial_expression=facial_expression,
            head_motion=head_motion,
            prompt_template=prompt_template,
        )
        return LiveAvatarRenderRequest(
            session_id=session_id,
            turn_id=turn_id,
            audio_path=audio_path,
            ref_image_path=ref_image_path,
            prompt=prompt,
            num_clip=max(int(num_clip), 1),
            metadata=metadata or {},
        )

    @staticmethod
    def build_prompt(
        *,
        emotion_style: str,
        facial_expression: str,
        head_motion: str,
        prompt_template: str,
    ) -> str:
        emotion = (emotion_style or "supportive").strip().lower()
        expression = (facial_expression or "neutral").strip().lower()
        motion = (head_motion or "steady").strip().lower()
        emotion_prompt = _resolve_emotion_prompt(emotion, expression)
        motion_prompt = _resolve_motion_prompt(motion)
        template = prompt_template.strip() or (
            "A person speaks naturally. {emotion_prompt} {motion_prompt} "
            "Accurate lip synchronization, expressive eyes and eyebrows, realistic motion, static camera."
        )
        return (
            template.replace("{emotion_style}", emotion)
            .replace("{facial_expression}", expression)
            .replace("{head_motion}", motion)
            .replace("{emotion_prompt}", emotion_prompt)
            .replace("{motion_prompt}", motion_prompt)
        )

    def render_video(
        self,
        request: LiveAvatarRenderRequest,
        *,
        runner_path: str,
        output_root: str,
        timeout_seconds: float,
    ) -> LiveAvatarRenderResult:
        runner = Path(runner_path).expanduser()
        if not runner.is_file():
            raise FileNotFoundError(f"LiveAvatar runner does not exist: {runner}")
        image = Path(request.ref_image_path).expanduser()
        if not image.is_file():
            raise FileNotFoundError(f"LiveAvatar reference image does not exist: {image}")
        audio = Path(request.audio_path).expanduser()
        if not audio.is_file():
            raise FileNotFoundError(f"LiveAvatar audio does not exist: {audio}")

        output_dir = Path(output_root).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_session_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.session_id).strip("._") or "session"
        output_path = output_dir / f"{safe_session_id}-{request.turn_id}.mp4"
        completed = subprocess.run(  # noqa: S603
            [
                str(runner),
                str(image),
                str(audio),
                str(output_path),
                request.prompt,
                str(request.num_clip),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "LiveAvatar render failed. "
                f"exit_code={completed.returncode}; "
                f"stdout={completed.stdout[-1600:]}; "
                f"stderr={completed.stderr[-1600:]}"
            )
        if not output_path.is_file():
            raise RuntimeError(f"LiveAvatar finished but output was not created: {output_path}")
        return LiveAvatarRenderResult(
            video_path=str(output_path),
            audio_path=str(audio),
            ref_image_path=str(image),
            metadata={"prompt": request.prompt, **request.metadata},
        )


def _resolve_emotion_prompt(emotion: str, expression: str) -> str:
    combined = f"{emotion} {expression}"
    mappings = (
        (("concern", "worried", "worry", "anxious", "担忧", "担心", "焦虑"),
         "She looks visibly concerned and empathetic, with worried eyes, slightly drawn eyebrows, and restrained tension."),
        (("sad", "sorrow", "悲伤", "难过"),
         "She looks clearly sad and subdued, with softened eyes and restrained sorrow."),
        (("happy", "joy", "smile", "开心", "高兴", "微笑"),
         "She looks genuinely happy and warm, with a clear natural smile and lively eyes."),
        (("serious", "firm", "严肃", "坚定"),
         "She looks serious, focused, and composed, with firm eye contact."),
        (("surprise", "surprised", "惊讶"),
         "She looks clearly surprised, with widened eyes and raised eyebrows."),
    )
    for keywords, prompt in mappings:
        if any(keyword in combined for keyword in keywords):
            return prompt
    return "She looks attentive, supportive, and emotionally engaged."


def _resolve_motion_prompt(motion: str) -> str:
    if any(keyword in motion for keyword in ("open", "gesture", "hand", "手势", "张开")):
        return "She uses visible, synchronized open-hand conversational gestures near chest level."
    if any(keyword in motion for keyword in ("nod", "点头")):
        return "She makes subtle natural nods and small supportive hand gestures."
    if any(keyword in motion for keyword in ("lean", "前倾")):
        return "She leans forward slightly and uses restrained empathetic hand gestures."
    return "She uses natural restrained conversational hand gestures and subtle head motion."


liveavatar_render_bridge = LiveAvatarRenderBridge()
