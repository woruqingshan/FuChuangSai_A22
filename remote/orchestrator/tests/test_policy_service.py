import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from models import ChatRequest
from services.policy_service import policy_service


class PolicyServiceTests(unittest.TestCase):
    def test_chinese_worry_selects_gentle_concern(self) -> None:
        request = ChatRequest(
            session_id="test-policy",
            turn_id=1,
            user_text="\u6211\u5bf9\u660e\u5929\u7684\u8003\u8bd5\u5f88\u62c5\u5fc3",
            input_type="text",
        )

        self.assertEqual(policy_service.select_emotion_style(request, request.user_text), "gentle")
        action = policy_service.select_avatar_action(request, request.user_text)
        self.assertEqual(action.facial_expression, "soft_concern")
        self.assertEqual(action.head_motion, "slow_nod")


if __name__ == "__main__":
    unittest.main()
