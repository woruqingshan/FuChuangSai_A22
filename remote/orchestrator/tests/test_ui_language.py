import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.llm_client import LLMClient, LLMRequest, LLMResult, VllmProvider
from models import ChatRequest, ContextMessage
from pydantic import ValidationError


class CapturingProvider:
    async def complete(self, request):
        self.request = request
        return LLMResult(reply_text="A reply", response_source="test")


class InterfaceLanguageTests(unittest.IsolatedAsyncioTestCase):
    async def test_interface_wins_over_text_history_and_server_default(self):
        client = LLMClient()
        provider = CapturingProvider()
        client._provider = provider
        with patch("adapters.llm_client.settings.response_language", "spanish"):
            for language, expected, text in [
                ("es", "Spanish", "Hello"),
                ("es", "Spanish", "Descansa."),
                ("es", "Spanish", "Hoy estoy algo cansado. He dormido poco."),
                ("en", "English", "Hola, gracias."),
                ("es", "Spanish", "OK"),
            ]:
                with self.subTest(language=language, text=text):
                    request = LLMRequest(
                        session_id="same-session", turn_id=1, system_prompt="Be helpful.",
                        user_text=text, input_mode="audio", ui_language=language,
                        context_messages=[ContextMessage(role="assistant", content="Hello. Hola.")],
                        context_summary="",
                    )
                    await client.generate_reply(request)
                    self.assertEqual(provider.request.response_language, expected)
                    self.assertIn(f"in natural {expected}", provider.request.system_prompt)

    async def test_current_language_instruction_follows_previous_language_history(self):
        import httpx
        from unittest.mock import AsyncMock
        request = LLMRequest(
            session_id="s", turn_id=2, system_prompt="Be helpful.",
            user_text="Hola, gracias.", input_mode="text", response_language="English",
            context_messages=[ContextMessage(role="assistant", content="Hola, estoy contigo.")],
            context_summary="",
        )
        fake = AsyncMock()
        fake.post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": "You are welcome."}}]},
            request=httpx.Request("POST", "http://test/chat"),
        )
        with patch("adapters.llm_client.httpx.AsyncClient") as cls:
            cls.return_value.__aenter__.return_value = fake
            await VllmProvider().complete(request)
        messages = fake.post.call_args.kwargs["json"]["messages"]
        self.assertEqual(messages[-1]["role"], "user")
        self.assertTrue(messages[-1]["content"].endswith("Reply entirely in English."))

    def test_invalid_interface_language_is_rejected(self):
        with self.assertRaises(ValidationError):
            ChatRequest(session_id="s", turn_id=1, ui_language="auto")

    def test_legacy_client_uses_configured_default(self):
        client = LLMClient()
        with patch("adapters.llm_client.settings.response_language", "auto"):
            self.assertEqual(client._resolve_response_language(), "English")
        with patch("adapters.llm_client.settings.response_language", "es"):
            self.assertEqual(client._resolve_response_language(), "Spanish")


if __name__ == "__main__":
    unittest.main()
