import sys
import unittest
from pathlib import Path
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import ChatRequest, RemoteChatRequest
from services.input_preprocessor import normalize_chat_request


class InterfaceLanguageBridgeTests(unittest.TestCase):
    def test_language_survives_text_audio_and_serialization(self):
        for language in ("en", "es"):
            for turn in ({"user_text": "OK"}, {"audio_base64": "YXVkaW8=", "audio_format": "wav"}):
                with self.subTest(language=language, turn=turn):
                    request = ChatRequest(ui_language=language, **turn)
                    remote = normalize_chat_request(request, "session", 1)
                    self.assertEqual(remote.ui_language, language)
                    self.assertEqual(RemoteChatRequest.model_validate(remote.model_dump()).ui_language, language)

    def test_invalid_language_is_rejected_and_legacy_clients_remain_valid(self):
        with self.assertRaises(ValidationError):
            ChatRequest(user_text="hello", ui_language="auto")
        self.assertIsNone(normalize_chat_request(ChatRequest(user_text="hello"), "session", 1).ui_language)


if __name__ == "__main__":
    unittest.main()
