import asyncio
from datetime import UTC, datetime, timedelta
import sys
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

EDGE_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(EDGE_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(EDGE_BACKEND_ROOT))

from config import settings  # noqa: E402

TEST_CODE = f"phase9-code-{uuid4().hex}"
settings.redis_key_prefix = f"a22test:{uuid4().hex}"
settings.invitation_codes = [{"code": TEST_CODE, "enabled": True, "max_uses": 100}]

import services.job_manager as job_module  # noqa: E402
from app import app  # noqa: E402
from models import ChatResponse, RemoteChatRequest  # noqa: E402
from services.access_service import AccessError, AccessService  # noqa: E402
from services.auth_service import auth_service  # noqa: E402
from services.db import db_session  # noqa: E402
from services.db_models import Account, InvitationCode  # noqa: E402
from services.job_manager import JobError, JobManager  # noqa: E402
from services.rate_limiter import FixedWindowRateLimiter  # noqa: E402
from services.security import fingerprint_secret  # noqa: E402
from services.session_service import SessionService  # noqa: E402
from services.storage import redis_store  # noqa: E402


def make_request(session_id: str, turn_id: int) -> RemoteChatRequest:
    return RemoteChatRequest(
        session_id=session_id,
        turn_id=turn_id,
        user_text="hello",
        input_type="text",
    )


def make_response(*, with_video: bool = True) -> ChatResponse:
    return ChatResponse(
        server_status="ok",
        reply_text="你好，我是知心伴行。",
        emotion_style="supportive",
        avatar_action={
            "facial_expression": "neutral",
            "head_motion": "steady",
        },
        reply_video_stream_url="/media/video-stream/sess_test/1/manifest" if with_video else None,
    )


class Phase9PersistenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        AccessService().sync_invitation_codes()

    @classmethod
    def tearDownClass(cls) -> None:
        for key in redis_store.client.scan_iter(match=f"{settings.redis_key_prefix}:*"):
            redis_store.client.delete(key)

    def test_access_grant_survives_service_recreation_and_invitation_usage_persists(self):
        session_service = SessionService(ttl_seconds=86400)
        session, _session_token, _created = session_service.bootstrap_session(None)
        service = AccessService()
        grant, token, created = service.verify_code(session=session, access_token=None, code=TEST_CODE)

        self.assertTrue(created)
        self.assertEqual(grant.access_token, token)
        self.assertTrue(AccessService().is_authorized(session=session, access_token=token))

        with db_session() as db:
            stored = db.query(InvitationCode).filter(
                InvitationCode.code_fingerprint == fingerprint_secret(TEST_CODE)
            ).one()
            self.assertGreaterEqual(stored.used_count, 1)

    def test_exhausted_invitation_is_rejected(self):
        code = f"single-use-{uuid4().hex}"
        old_codes = settings.invitation_codes
        settings.invitation_codes = [{"code": code, "enabled": True, "max_uses": 1}]
        service = AccessService()
        service.sync_invitation_codes()
        session_service = SessionService(ttl_seconds=86400)
        session_a, _token_a, _ = session_service.bootstrap_session(None)
        session_b, _token_b, _ = session_service.bootstrap_session(None)
        try:
            service.verify_code(session=session_a, access_token=None, code=code)
            with self.assertRaises(AccessError):
                service.verify_code(session=session_b, access_token=None, code=code)
        finally:
            settings.invitation_codes = old_codes

    def test_rate_limit_survives_limiter_recreation(self):
        limiter = FixedWindowRateLimiter()
        key = f"phase9-rate:{uuid4().hex}"
        self.assertTrue(limiter.allow(key, limit=2, window_seconds=600).allowed)
        self.assertTrue(FixedWindowRateLimiter().allow(key, limit=2, window_seconds=600).allowed)
        result = FixedWindowRateLimiter().allow(key, limit=2, window_seconds=600)
        self.assertFalse(result.allowed)
        self.assertGreater(result.retry_after_seconds, 0)


class JobManagerPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._old_orchestrator = job_module.orchestrator_client
        self._old_max_pending = settings.job_queue_max_pending
        self._old_retention = settings.job_retention_seconds

    async def asyncTearDown(self):
        job_module.orchestrator_client = self._old_orchestrator
        settings.job_queue_max_pending = self._old_max_pending
        settings.job_retention_seconds = self._old_retention
        for key in redis_store.client.scan_iter(match=f"{settings.redis_key_prefix}:*"):
            redis_store.client.delete(key)

    async def test_capacity_applies_before_worker_claims_first_job_and_queue_persists(self):
        settings.job_queue_max_pending = 2
        manager = JobManager()
        accepted_jobs = []
        for index in range(1 + settings.job_queue_max_pending):
            accepted_jobs.append(
                await manager.submit(
                    session_id=f"sess_capacity_{index}",
                    turn_id=1,
                    request=make_request(f"sess_capacity_{index}", 1),
                )
            )

        self.assertEqual(len(accepted_jobs), 3)
        self.assertEqual(await manager.queue_position(accepted_jobs[0].job_id), 1)
        self.assertEqual((await JobManager().get(accepted_jobs[1].job_id)).status, "queued")

        with self.assertRaises(JobError) as queue_error:
            await manager.submit(
                session_id="sess_capacity_overflow",
                turn_id=1,
                request=make_request("sess_capacity_overflow", 1),
            )
        self.assertEqual(queue_error.exception.status_code, 429)

    async def test_one_active_job_per_session_is_redis_backed(self):
        manager = JobManager()
        first = await manager.submit(session_id="sess_one_active", turn_id=1, request=make_request("sess_one_active", 1))
        self.assertEqual(first.status, "queued")
        with self.assertRaises(JobError) as active_error:
            await JobManager().submit(
                session_id="sess_one_active",
                turn_id=2,
                request=make_request("sess_one_active", 2),
            )
        self.assertEqual(active_error.exception.status_code, 409)

    async def test_processing_recovery_fails_without_resending(self):
        manager = JobManager()
        job = await manager.submit(session_id="sess_processing", turn_id=1, request=make_request("sess_processing", 1))
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        manager._save_job(job)
        recovered = JobManager()
        recovered._recover_jobs_after_restart()
        self.assertEqual((await recovered.get(job.job_id)).status, "failed")
        self.assertEqual((await recovered.get(job.job_id)).error, "edge_restarted_during_processing")

    async def test_rendering_recovery_resumes_manifest_monitor(self):
        manager = JobManager()
        job = await manager.submit(session_id="sess_rendering", turn_id=1, request=make_request("sess_rendering", 1))
        job.status = "rendering"
        job.started_at = datetime.now(UTC)
        job.chat_response = make_response(with_video=True)
        manager._save_job(job)
        redis_store.client.set(manager._active_key(), job.job_id)

        recovered = JobManager()

        async def complete_manifest(job_record, manifest_url):
            recovered._finish_job(job_record, status="completed")

        recovered._wait_for_manifest_complete = complete_manifest
        await recovered.start()
        try:
            await asyncio.sleep(0.1)
            self.assertEqual((await recovered.get(job.job_id)).status, "completed")
        finally:
            await recovered.stop()


class AuthRouteTest(unittest.TestCase):
    def test_register_login_me_logout_and_session_binding(self):
        settings.redis_key_prefix = f"a22testauth:{uuid4().hex}"
        username = f"phase9_user_{uuid4().hex[:12]}"
        password = "phase9-password"
        with TestClient(app, base_url="https://testserver") as client:
            session_response = client.post("/session")
            self.assertEqual(session_response.status_code, 200)
            first_session_id = session_response.json()["session_id"]
            self.assertEqual(client.get("/auth/me").json(), {"authenticated": False, "user": None})

            access_response = client.post("/access/verify", json={"code": TEST_CODE})
            self.assertEqual(access_response.status_code, 200)

            register_response = client.post("/auth/register", json={"username": username, "password": password})
            self.assertEqual(register_response.status_code, 200)
            self.assertTrue(register_response.json()["authenticated"])

            with db_session() as db:
                account = db.query(Account).filter(Account.username_normalized == username.lower()).one()
                self.assertTrue(account.password_hash.startswith("$argon2"))
                self.assertNotEqual(account.password_hash, password)

            duplicate_response = client.post("/auth/register", json={"username": username, "password": password})
            self.assertEqual(duplicate_response.status_code, 409)

            me_response = client.get("/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertTrue(me_response.json()["authenticated"])

            same_session_response = client.post("/session")
            self.assertEqual(same_session_response.json()["session_id"], first_session_id)

            logout_response = client.post("/auth/logout")
            self.assertEqual(logout_response.status_code, 200)
            self.assertFalse(client.get("/auth/me").json()["authenticated"])

            bad_login_response = client.post("/auth/login", json={"username": username, "password": "wrong-pass"})
            self.assertEqual(bad_login_response.status_code, 401)
            self.assertEqual(bad_login_response.json()["detail"], "用户名或密码错误")

            login_response = client.post("/auth/login", json={"username": username, "password": password})
            self.assertEqual(login_response.status_code, 200)
            self.assertTrue(client.get("/auth/me").json()["authenticated"])
            self.assertEqual(client.post("/session").json()["session_id"], first_session_id)
        for key in redis_store.client.scan_iter(match=f"{settings.redis_key_prefix}:*"):
            redis_store.client.delete(key)


if __name__ == "__main__":
    unittest.main()
