import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.tts_runtime import TTSRuntime


class InterfaceVoiceTests(unittest.TestCase):
    def test_explicit_spanish_routes_a_reply_without_markers_to_spanish_voice(self):
        with patch("services.tts_runtime.settings.edge_spanish_tts_enabled", True):
            self.assertTrue(TTSRuntime()._should_use_edge_spanish("Descansa.", ui_language="es"))

    def test_explicit_english_does_not_switch_voice_based_on_words(self):
        with patch("services.tts_runtime.settings.edge_spanish_tts_enabled", True):
            self.assertFalse(TTSRuntime()._should_use_edge_spanish("Hola, gracias.", ui_language="en"))


if __name__ == "__main__":
    unittest.main()
