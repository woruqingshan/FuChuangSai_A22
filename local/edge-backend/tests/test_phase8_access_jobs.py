import asyncio
from datetime import UTC, datetime, timedelta
import unittest

from fastapi.testclient import TestClient

import services.access_service as access_module
import services.job_manager as job_module
from app import app
from config import settings
from models import ChatResponse, RemoteChatRequest
from services.access_service import AccessError, AccessService
from services.job_manager import JobError, JobManager
from services.rate_limiter import FixedWindowRateLimiter
from services.session_service import SessionRecord, session_service


def make_session(session_id: str) -> SessionRecord:
    now = datetime.now(UTC)
    return SessionRecord(
        cookie_token=f"token-{session_id}",
        session_id=session_id,
        stream_id=f"stream-{session_id}",
        created_at=now,
        last_seen_at=now,
    )


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


class AccessServiceTest(unittest.TestCase):
    def test_valid_invalid_and_exhausted_invitation(self):
        old_codes = settings.invitation_codes
        settings.invitation_codes = [
            {"code": "valid-code", "enabled": True, "max_uses": 1},
            {"code": "disabled-code", "enabled": False},
            {
                "code": "expired-code",
                "enabled": True,
                "expires_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            },
        ]
        try:
            service = AccessService()
            session = make_session("sess_a")

            grant, token, created = service.verify_code(session=session, access_token=None, code="valid-code")
            self.assertTrue(created)
            self.assertEqual(grant.access_token, token)
            self.assertTrue(service.is_authorized(session=session, access_token=token))

            reused, reused_token, reused_created = service.verify_code(
                session=session,
                access_token=token,
                code="valid-code",
            )
            self.assertFalse(reused_created)
            self.assertEqual(reused.access_token, reused_token)

            with self.assertRaises(AccessError):
                service.verify_code(session=make_session("sess_b"), access_token=None, code="valid-code")
            with self.assertRaises(AccessError):
                service.verify_code(session=make_session("sess_c"), access_token=None, code="disabled-code")
            with self.assertRaises(AccessError):
                service.verify_code(session=make_session("sess_d"), access_token=None, code="expired-code")
        finally:
            settings.invitation_codes = old_codes


class RateLimiterTest(unittest.TestCase):
    def test_fixed_window_limit(self):
        limiter = FixedWindowRateLimiter()
        self.assertTrue(limiter.allow("ip:1", limit=2, window_seconds=600).allowed)
        self.assertTrue(limiter.allow("ip:1", limit=2, window_seconds=600).allowed)
        result = limiter.allow("ip:1", limit=2, window_seconds=600)
        self.assertFalse(result.allowed)
        self.assertGreater(result.retry_after_seconds, 0)


class JobManagerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        job_module.orchestrator_client = self._old_orchestrator
        settings.job_queue_max_pending = self._old_max_pending
        settings.job_retention_seconds = self._old_retention

    async def asyncSetUp(self):
        self._old_orchestrator = job_module.orchestrator_client
        self._old_max_pending = settings.job_queue_max_pending
        self._old_retention = settings.job_retention_seconds

    async def test_active_job_queue_position_and_release_after_manifest_complete(self):
        class FakeOrchestrator:
            async def send_chat(self, request, *, request_id):
                return make_response(with_video=True)

        job_module.orchestrator_client = FakeOrchestrator()
        settings.job_queue_max_pending = 3
        release_manifest = asyncio.Event()
        manager = JobManager()

        async def wait_for_manifest(job, manifest_url):
            await release_manifest.wait()
            async with manager._lock:
                manager._finish_job_locked(job, status="completed")

        manager._wait_for_manifest_complete = wait_for_manifest
        await manager.start()
        try:
            first = await manager.submit(session_id="sess_a", turn_id=1, request=make_request("sess_a", 1))
            await asyncio.sleep(0.05)
            self.assertEqual((await manager.get(first.job_id)).status, "rendering")

            second = await manager.submit(session_id="sess_b", turn_id=1, request=make_request("sess_b", 1))
            self.assertEqual(await manager.queue_position(second.job_id), 1)
            self.assertEqual((await manager.get(second.job_id)).status, "queued")

            release_manifest.set()
            await asyncio.sleep(0.1)
            self.assertEqual((await manager.get(first.job_id)).status, "completed")
            self.assertIn((await manager.get(second.job_id)).status, {"processing", "rendering", "completed"})
        finally:
            release_manifest.set()
            await manager.stop()

    async def test_one_active_job_per_session_and_queue_full(self):
        settings.job_queue_max_pending = 1
        manager = JobManager()
        first = await manager.submit(session_id="sess_a", turn_id=1, request=make_request("sess_a", 1))
        self.assertEqual(first.status, "queued")
        with self.assertRaises(JobError) as active_error:
            await manager.submit(session_id="sess_a", turn_id=2, request=make_request("sess_a", 2))
        self.assertEqual(active_error.exception.status_code, 409)

        manager._active_job_id = first.job_id
        manager._queue.remove(first.job_id)
        second = await manager.submit(session_id="sess_b", turn_id=1, request=make_request("sess_b", 1))
        self.assertEqual(await manager.queue_position(second.job_id), 1)
        with self.assertRaises(JobError) as queue_error:
            await manager.submit(session_id="sess_c", turn_id=1, request=make_request("sess_c", 1))
        self.assertEqual(queue_error.exception.status_code, 429)


class JobRouteAuthorizationTest(unittest.TestCase):
    def test_cross_session_job_access_denied(self):
        client = TestClient(app)
        record_a, token_a, _created_a = session_service.bootstrap_session(None)
        record_b, token_b, _created_b = session_service.bootstrap_session(None)
        job_module.job_manager._jobs["job_route_test"] = job_module.JobRecord(
            job_id="job_route_test",
            session_id=record_a.session_id,
            turn_id=1,
            request=make_request(record_a.session_id, 1),
            status="queued",
            created_at=datetime.now(UTC),
        )

        old_require_access = access_module.access_service.require_access
        access_module.access_service.require_access = lambda *, session, access_token: object()
        try:
            response = client.get(
                "/jobs/job_route_test",
                cookies={settings.session_cookie_name: token_b, settings.access_cookie_name: "access-b"},
            )
            self.assertEqual(response.status_code, 403)

            response = client.get(
                "/jobs/job_route_test",
                cookies={settings.session_cookie_name: token_a, settings.access_cookie_name: "access-a"},
            )
            self.assertEqual(response.status_code, 200)
        finally:
            access_module.access_service.require_access = old_require_access
            job_module.job_manager._jobs.pop("job_route_test", None)


if __name__ == "__main__":
    unittest.main()
