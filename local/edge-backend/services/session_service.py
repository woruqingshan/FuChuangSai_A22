from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import secrets

from config import settings
from models import TurnTimeWindow


BEIJING_TZ = timezone(timedelta(hours=8))


class SessionError(Exception):
    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class SessionRecord:
    cookie_token: str
    session_id: str
    stream_id: str
    created_at: datetime
    last_seen_at: datetime
    next_turn_id: int = 1


class SessionService:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions_by_token: dict[str, SessionRecord] = {}
        self._last_cleanup_at = datetime.now(UTC)

    def bootstrap_session(self, cookie_token: str | None) -> tuple[SessionRecord, str, bool]:
        now = self._now()
        self._cleanup_if_due(now)
        if cookie_token:
            record = self._sessions_by_token.get(cookie_token)
            if record and not self._is_expired(record, now):
                record.last_seen_at = now
                return record, cookie_token, False

        new_token = secrets.token_urlsafe(32)
        record = SessionRecord(
            cookie_token=new_token,
            session_id=self._generate_session_id(now),
            stream_id=self._generate_stream_id(now),
            created_at=now,
            last_seen_at=now,
        )
        self._sessions_by_token[new_token] = record
        return record, new_token, True

    def require_session(self, cookie_token: str | None) -> SessionRecord:
        now = self._now()
        self._cleanup_if_due(now)
        if not cookie_token:
            raise SessionError("Anonymous session is required.", status_code=401)
        record = self._sessions_by_token.get(cookie_token)
        if not record or self._is_expired(record, now):
            if record:
                self._sessions_by_token.pop(cookie_token, None)
            raise SessionError("Anonymous session is missing or expired.", status_code=401)
        record.last_seen_at = now
        return record

    def allocate_turn(self, record: SessionRecord) -> int:
        turn_id = record.next_turn_id
        record.next_turn_id += 1
        record.last_seen_at = self._now()
        return turn_id

    def authorize_media_session(self, cookie_token: str | None, path_session_id: str) -> SessionRecord:
        record = self.require_session(cookie_token)
        if path_session_id != record.session_id:
            raise SessionError("Media does not belong to the current session.", status_code=403)
        return record

    def canonical_turn_time_window(
        self,
        *,
        record: SessionRecord,
        turn_id: int,
        client_window: TurnTimeWindow | None,
    ) -> TurnTimeWindow:
        if client_window:
            if hasattr(client_window, "model_copy"):
                payload = client_window.model_dump()
            else:
                payload = client_window.dict()
        else:
            now_ms = int(self._now().timestamp() * 1000)
            payload = {
                "source_clock": "server_beijing_epoch_ms",
                "transport_mode": "http_turn",
                "capture_started_at_ms": now_ms,
                "capture_ended_at_ms": now_ms,
                "window_duration_ms": 0,
            }

        payload.update(
            {
                "window_id": f"{record.session_id}-turn-{turn_id}",
                "stream_id": record.stream_id,
                "sequence_id": turn_id,
            }
        )
        return TurnTimeWindow(**payload)

    def expire_old_sessions(self, *, now: datetime | None = None) -> int:
        current = now or self._now()
        expired_tokens = [
            token for token, record in self._sessions_by_token.items() if self._is_expired(record, current)
        ]
        for token in expired_tokens:
            self._sessions_by_token.pop(token, None)
        self._last_cleanup_at = current
        return len(expired_tokens)

    def _cleanup_if_due(self, now: datetime) -> None:
        if (now - self._last_cleanup_at).total_seconds() >= 300:
            self.expire_old_sessions(now=now)

    def _is_expired(self, record: SessionRecord, now: datetime) -> bool:
        return (now - record.last_seen_at).total_seconds() > self._ttl_seconds

    def _generate_session_id(self, now: datetime) -> str:
        return f"sess_{self._format_beijing_timestamp(now)}_{secrets.token_hex(16)}"

    def _generate_stream_id(self, now: datetime) -> str:
        return f"stream_{self._format_beijing_timestamp(now)}_{secrets.token_hex(8)}"

    @staticmethod
    def _format_beijing_timestamp(now: datetime) -> str:
        return now.astimezone(BEIJING_TZ).strftime("%Y%m%dT%H%M%SCST")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)


session_service = SessionService(ttl_seconds=settings.session_ttl_seconds)
