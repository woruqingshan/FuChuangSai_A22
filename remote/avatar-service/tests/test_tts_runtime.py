import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from services.tts_runtime import TTSRuntime


class TTSRuntimeInstructTests(unittest.TestCase):
    def test_300m_prompt_keeps_required_separator(self):
        runtime = TTSRuntime()
        self.assertEqual(
            runtime._normalize_cosyvoice300m_prompt("concerned caregiver"),
            "concerned caregiver<|endofprompt|>",
        )
        self.assertEqual(
            runtime._normalize_cosyvoice300m_prompt("concerned caregiver<|endofprompt|>"),
            "concerned caregiver<|endofprompt|>",
        )

    def test_300m_mode_uses_safe_non_instruct_inference(self):
        runtime = TTSRuntime()
        model = object()
        with (
            patch("services.tts_runtime.settings.tts_mode", "cosyvoice_300m_instruct"),
            patch.object(runtime, "_invoke_300m_safe", return_value="audio") as invoke,
        ):
            result = runtime._invoke_tts(
                model,
                "正文",
                instruct_text="concerned caregiver",
                speed=1.0,
                speaker_id="中文女",
            )

        self.assertEqual(result, "audio")
        invoke.assert_called_once_with(
            model,
            "正文",
            speed=1.0,
            speaker_id="中文女",
        )

    def test_300m_instruct_normalizes_prompt_but_not_spoken_text(self):
        runtime = TTSRuntime()
        fake_model = SimpleNamespace(
            inference_instruct=lambda **kwargs: kwargs,
        )
        with (
            patch("services.tts_runtime.settings.tts_mode", "cosyvoice_300m_instruct"),
            patch("services.tts_runtime.settings.tts_instruct_text", "concerned caregiver"),
            patch("services.tts_runtime.settings.tts_speaker_id", "中文女"),
        ):
            result = runtime._invoke_instruct(fake_model, "正文")

        self.assertEqual(result["tts_text"], "正文")
        self.assertEqual(result["instruct_text"], "concerned caregiver<|endofprompt|>")


if __name__ == "__main__":
    unittest.main()
