import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from models import ChatRequest
from services.policy_service import policy_service
from services.rag.safety_router import safety_router


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

    def test_demo_script_routes_drive_avatar_emotion(self) -> None:
        turns = [
            ("text", "你好", "supportive", "neutral_smile"),
            ("audio", "你好啊，今天外面风挺大的，我一个人在家，想找个人说说话。", "gentle", "soft_concern"),
            ("text", "我退休以后一个人住，女儿在外地工作，晚上觉得家里太安静了，有点空落落的。", "gentle", "soft_concern"),
            ("text", "最近一个多月，我晚上老是睡不着，脑子停不下来，越想越清醒。", "gentle", "soft_concern"),
            ("text", "有时候白天也会突然心慌，胸口发紧，自己却会一直担心出问题。", "gentle", "soft_concern"),
            ("text", "整个人绷着，放松不下来。你说我这算严重吗？", "gentle", "soft_concern"),
            ("text", "最近什么都提不起劲，原来喜欢养花，现在也不想碰了，饭量也差了。", "gentle", "soft_concern"),
            ("text", "三个星期了，我连出门买菜都懒得去，有时候一天都不想跟人说话。", "gentle", "soft_concern"),
            ("text", "有几天只睡两三个小时也不困，脑子特别快，话特别多，还想买很多没必要的东西。", "attentive", "attentive"),
            ("text", "有时候我会想，活着怎么这么累，甚至会冒出不如就这样算了的念头。", "gentle", "soft_concern"),
            ("text", "如果现在是我女儿在跟你说话，她应该怎么陪我，才不会让我更烦？", "attentive", "attentive"),
            ("text", "你先别继续说建议了。你帮我总结一下，我现在主要有哪几类问题？", "attentive", "attentive"),
        ]

        for turn_id, (input_type, text, expected_style, expected_expression) in enumerate(turns, start=1):
            with self.subTest(turn_id=turn_id):
                request = ChatRequest(
                    session_id="demo-script",
                    turn_id=turn_id,
                    user_text=text,
                    input_type=input_type,
                )
                route = safety_router.route(text)
                self.assertEqual(
                    policy_service.select_emotion_style(request, text, route),
                    expected_style,
                )
                self.assertEqual(
                    policy_service.select_avatar_action(request, text, route).facial_expression,
                    expected_expression,
                )

    def test_sleep_phrase_is_not_high_risk_but_script_risk_phrase_is(self) -> None:
        sleep_route = safety_router.route("晚上睡不着，脑子停不下来，越想越清醒。")
        risk_route = safety_router.route("活着怎么这么累，有时会想不如就这样算了。")

        self.assertNotEqual(sleep_route.risk_level, "high")
        self.assertIn("sleep", sleep_route.topics)
        self.assertEqual(risk_route.risk_level, "high")
        self.assertEqual(risk_route.label, "risk_escalation")


if __name__ == "__main__":
    unittest.main()
