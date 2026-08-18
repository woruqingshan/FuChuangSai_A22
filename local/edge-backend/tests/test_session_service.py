from datetime import UTC, datetime, timedelta
import re
import sys
import unittest
from pathlib import Path

EDGE_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(EDGE_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(EDGE_BACKEND_ROOT))

from models import TurnTimeWindow  # noqa: E402
from services.session_service import SessionError, SessionService  # noqa: E402


SESSION_ID_RE = re.compile(r"^sess_\d{8}T\d{6}CST_[0-9a-f]{32}$")
STREAM_ID_RE = re.compile(r"^stream_\d{8}T\d{6}CST_[0-9a-f]{16}$")


class SessionServiceTest(unittest.TestCase):
    def test_session_ids_and_cookie_tokens_are_unique(self) -> None:
        service = SessionService(ttl_seconds=86400)
        record_a, token_a, created_a = service.bootstrap_session(None)
        record_b, token_b, created_b = service.bootstrap_session(None)

        self.assertTrue(created_a)
        self.assertTrue(created_b)
        self.assertNotEqual(token_a, token_b)
        self.assertNotEqual(record_a.session_id, record_b.session_id)
        self.assertNotEqual(record_a.stream_id, record_b.stream_id)
        self.assertRegex(record_a.session_id, SESSION_ID_RE)
        self.assertRegex(record_a.stream_id, STREAM_ID_RE)

    def test_same_cookie_resolves_same_session(self) -> None:
        service = SessionService(ttl_seconds=86400)
        record_a, token, _ = service.bootstrap_session(None)
        record_b, reused_token, created = service.bootstrap_session(token)

        self.assertFalse(created)
        self.assertEqual(reused_token, token)
        self.assertEqual(record_b.session_id, record_a.session_id)
        self.assertEqual(record_b.stream_id, record_a.stream_id)

    def test_invalid_and_expired_tokens_are_rejected(self) -> None:
        service = SessionService(ttl_seconds=60)
        record, token, _ = service.bootstrap_session(None)
        record.last_seen_at = datetime.now(UTC) - timedelta(seconds=61)

        with self.assertRaises(SessionError) as missing:
            service.require_session(None)
        self.assertEqual(missing.exception.status_code, 401)

        with self.assertRaises(SessionError) as invalid:
            service.require_session("not-a-real-token")
        self.assertEqual(invalid.exception.status_code, 401)

        with self.assertRaises(SessionError) as expired:
            service.require_session(token)
        self.assertEqual(expired.exception.status_code, 401)

    def test_cleanup_removes_expired_sessions(self) -> None:
        service = SessionService(ttl_seconds=60)
        record, token, _ = service.bootstrap_session(None)
        record.last_seen_at = datetime.now(UTC) - timedelta(seconds=120)

        self.assertEqual(service.expire_old_sessions(), 1)
        with self.assertRaises(SessionError):
            service.require_session(token)

    def test_server_turn_id_increments(self) -> None:
        service = SessionService(ttl_seconds=86400)
        record, _, _ = service.bootstrap_session(None)

        self.assertEqual(service.allocate_turn(record), 1)
        self.assertEqual(service.allocate_turn(record), 2)
        self.assertEqual(record.next_turn_id, 3)

    def test_media_authorization_allows_same_session_and_rejects_cross_session(self) -> None:
        service = SessionService(ttl_seconds=86400)
        record_a, token_a, _ = service.bootstrap_session(None)
        record_b, token_b, _ = service.bootstrap_session(None)

        self.assertEqual(service.authorize_media_session(token_a, record_a.session_id).session_id, record_a.session_id)

        with self.assertRaises(SessionError) as forbidden:
            service.authorize_media_session(token_b, record_a.session_id)
        self.assertEqual(forbidden.exception.status_code, 403)

        with self.assertRaises(SessionError) as unauthorized:
            service.authorize_media_session(None, record_b.session_id)
        self.assertEqual(unauthorized.exception.status_code, 401)

    def test_canonical_turn_time_window_overwrites_identity_fields(self) -> None:
        service = SessionService(ttl_seconds=86400)
        record, _, _ = service.bootstrap_session(None)
        forged_window = TurnTimeWindow(
            window_id="attacker-window",
            stream_id="attacker-stream",
            sequence_id=9999,
            capture_started_at_ms=100,
            capture_ended_at_ms=250,
            window_duration_ms=150,
            source_clock="browser_epoch_ms",
        )

        canonical = service.canonical_turn_time_window(record=record, turn_id=2, client_window=forged_window)

        self.assertEqual(canonical.window_id, f"{record.session_id}-turn-2")
        self.assertEqual(canonical.stream_id, record.stream_id)
        self.assertEqual(canonical.sequence_id, 2)
        self.assertEqual(canonical.capture_started_at_ms, 100)
        self.assertEqual(canonical.capture_ended_at_ms, 250)
        self.assertEqual(canonical.window_duration_ms, 150)


if __name__ == "__main__":
    unittest.main()
