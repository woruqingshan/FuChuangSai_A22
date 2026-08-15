import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from services.liveavatar_render_bridge import LiveAvatarRenderBridge


class LiveAvatarRenderBridgeTests(unittest.TestCase):
    def test_build_request_maps_concern_and_open_gesture(self) -> None:
        bridge = LiveAvatarRenderBridge()
        request = bridge.build_request(
            session_id="session-a",
            turn_id=3,
            audio_path="reply.wav",
            ref_image_path="portrait.jpg",
            emotion_style="concerned",
            facial_expression="soft_concern",
            head_motion="open_gesture",
            prompt_template="{emotion_prompt} {motion_prompt}",
            num_clip=10000,
        )

        self.assertIn("visibly concerned", request.prompt)
        self.assertIn("open-hand conversational gestures", request.prompt)

    def test_render_invokes_runner_without_shell_and_returns_exact_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runner = temp_path / "run_liveavatar.sh"
            image = temp_path / "portrait.jpg"
            audio = temp_path / "reply.wav"
            for path in (runner, image, audio):
                path.write_bytes(b"test")

            captured = {}

            def fake_run(args, **kwargs):
                captured["args"] = args
                captured["kwargs"] = kwargs
                Path(args[3]).write_bytes(b"video")
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

            bridge = LiveAvatarRenderBridge()
            request = bridge.build_request(
                session_id="session/unsafe",
                turn_id=7,
                audio_path=str(audio),
                ref_image_path=str(image),
                emotion_style="supportive",
                facial_expression="attentive",
                head_motion="slow_nod",
                prompt_template="",
                num_clip=10000,
            )

            with patch("services.liveavatar_render_bridge.subprocess.run", side_effect=fake_run):
                result = bridge.render_video(
                    request,
                    runner_path=str(runner),
                    output_root=str(temp_path / "outputs"),
                    timeout_seconds=30,
                )

            self.assertEqual(Path(result.video_path).name, "session_unsafe-7.mp4")
            self.assertEqual(captured["args"][0], str(runner))
            self.assertEqual(captured["args"][1:3], [str(image), str(audio)])
            self.assertEqual(captured["kwargs"]["timeout"], 30)
            self.assertFalse(captured["kwargs"]["check"])


if __name__ == "__main__":
    unittest.main()
