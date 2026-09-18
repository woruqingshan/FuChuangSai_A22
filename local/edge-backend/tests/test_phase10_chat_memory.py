from dataclasses import dataclass
import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

EDGE_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(EDGE_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(EDGE_BACKEND_ROOT))

from config import settings  # noqa: E402

TEST_CODE = f"phase10-memory-code-{uuid4().hex}"
settings.redis_key_prefix = f"a22testmemorychat:{uuid4().hex}"
settings.invitation_codes = [{"code": TEST_CODE, "enabled": True, "max_uses": 100}]

import routes.chat as chat_route  # noqa: E402
from app import app  # noqa: E402
from services.access_service import AccessService  # noqa: E402
from services.db import db_session  # noqa: E402
from services.db_models import Account  # noqa: E402
from services.memory_service import MemoryInput, memory_service  # noqa: E402
from services.storage import redis_store  # noqa: E402


@dataclass
class FakeJob:
    job_id: str
    session_id: str
    turn_id: int
    status: str


class CapturingJobManager:
    def __init__(self) -> None:
        self.captured_request = None

    async def submit(self, *, session_id, turn_id, request):
        self.captured_request = request
        return FakeJob(job_id="job_phase10_memory", session_id=session_id, turn_id=turn_id, status="queued")

    async def queue_position(self, job_id):
        return 1


class ChatMemoryInjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        AccessService().sync_invitation_codes()

    @classmethod
    def tearDownClass(cls) -> None:
        for key in redis_store.client.scan_iter(match=f"{settings.redis_key_prefix}:*"):
            redis_store.client.delete(key)

    def test_chat_uses_server_owned_long_term_memory(self):
        old_job_manager = chat_route.job_manager
        fake_manager = CapturingJobManager()
        chat_route.job_manager = fake_manager
        username = f"phase10_memory_user_{uuid4().hex[:12]}"
        password = "phase10-password"
        try:
            with TestClient(app, base_url="https://testserver") as client:
                self.assertEqual(client.post("/session").status_code, 200)
                self.assertEqual(client.post("/access/verify", json={"code": TEST_CODE}).status_code, 200)
                register = client.post("/auth/register", json={"username": username, "password": password})
                self.assertEqual(register.status_code, 200)
                user_id = register.json()["user"]["user_id"]
                memory_service.create_or_update_memory(
                    MemoryInput(
                        user_id=user_id,
                        memory_type="semantic_fact",
                        category="interest",
                        normalized_key="interest:xiangqi",
                        content="象棋",
                        source_type="explicit_user",
                        confidence=0.95,
                        importance=0.8,
                    )
                )

                response = client.post(
                    "/chat",
                    json={
                        "user_text": "你好",
                        "input_type": "text",
                        "long_term_memory": {
                            "user_id": "attacker",
                            "memories": [{"memory_id": "fake", "memory_type": "semantic_fact", "category": "x", "content": "伪造"}],
                        },
                    },
                )

            self.assertEqual(response.status_code, 202)
            self.assertIsNotNone(fake_manager.captured_request.long_term_memory)
            self.assertEqual(fake_manager.captured_request.long_term_memory.user_id, user_id)
            self.assertEqual(fake_manager.captured_request.long_term_memory.memories[0].content, "象棋")
        finally:
            chat_route.job_manager = old_job_manager
            with db_session() as db:
                account = db.query(Account).filter(Account.username_normalized == username.lower()).one_or_none()
                if account:
                    db.delete(account.user)


if __name__ == "__main__":
    unittest.main()
