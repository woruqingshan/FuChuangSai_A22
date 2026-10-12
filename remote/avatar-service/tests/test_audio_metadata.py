import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from routes.generate import _resolve_audio_meta


class AudioMetadataTests(unittest.TestCase):
    def test_real_audio_duration_replaces_text_estimate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "speech.wav"
            for frame_count in (3360, 240001):
                with self.subTest(frame_count=frame_count):
                    with wave.open(str(path), "wb") as audio:
                        audio.setnchannels(1)
                        audio.setsampwidth(2)
                        audio.setframerate(24000)
                        audio.writeframes(b"\0\0" * frame_count)
                    self.assertEqual(
                        _resolve_audio_meta(path, fallback_ms=8000),
                        (math.ceil(frame_count * 1000 / 24000), 24000),
                    )

    def test_missing_audio_uses_estimate(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                _resolve_audio_meta(Path(folder) / "missing.wav", fallback_ms=1200),
                (1200, None),
            )


if __name__ == "__main__":
    unittest.main()
