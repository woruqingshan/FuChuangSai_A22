from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import secrets

from config import settings
from models import TurnTimeWindow
from services.security import digest_token
from services.storage import redis_store


BEIJING_TZ = timezone(timedelta(hours=8))


class SessionError(Exception):
    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class SessionRecord:
    cookie_token: str
    token_digest: str
    session_id: str
    stream_id: str
    created_at: datetime
    last_seen_at: datetime
    next_turn_id: int = 1
    user_id: str | None = None


class SessionService:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._redis = redis_store.client

    def bootstrap_session(self, cookie_token: str | None) -> tuple[SessionRecord, str, bool]:
        if cookie_token:
            record = self._load_record(cookie_token)
            if record:
                self._touch(record)
                return record, cookie_token, False

        now = self._now()
        new_token = secrets.token_urlsafe(32)
        token_digest = digest_token(new_token)
        record = SessionRecord(
            cookie_token=new_token,
            token_digest=token_digest,
            session_id=self._generate_session_id(now),
            stream_id=self._generate_stream_id(now),
            created_at=now,
            last_seen_at=now,
        )
        self._save_record(record)
        return record, new_token, True

    def require_session(self, cookie_token: str | None) -> SessionRecord:
        if not cookie_token:
            raise SessionError("Anonymous session is required.", status_code=401)
        record = self._load_record(cookie_token)
        if not record:
            raise SessionError("Anonymous session is missing or expired.", status_code=401)
        self._touch(record)
        return record

    def allocate_turn(self, record: SessionRecord) -> int:
        key = self._key(record.token_digest)
        next_value = int(self._redis.hincrby(key, "next_turn_id", 1))
        self._redis.hset(key, mapping={"last_seen_at": self._serialize_dt(self._now())})
        self._redis.expire(key, self._ttl_seconds)
        record.next_turn_id = next_value
        return next_value - 1

    def bind_user(self, cookie_token: str | None, user_id: str) -> SessionRecord:
        record = self.require_session(cookie_token)
        key = self._key(record.token_digest)
        self._redis.hset(key, mapping={"user_id": user_id, "last_seen_at": self._serialize_dt(self._now())})
        self._redis.expire(key, self._ttl_seconds)
        record.user_id = user_id
        return record

    def clear_user(self, cookie_token: str | None) -> None:
        if not cookie_token:
            return
        token_digest = digest_token(cookie_token)
        key = self._key(token_digest)
        if self._redis.exists(key):
            self._redis.hdel(key, "user_id")
            self._redis.hset(key, mapping={"last_seen_at": self._serialize_dt(self._now())})
            self._redis.expire(key, self._ttl_seconds)

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
            if hasattr(client_window, "model_dump"):
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
        return 0

    def _save_record(self, record: SessionRecord) -> None:
        key = self._key(record.token_digest)
        self._redis.hset(
            key,
            mapping={
                "session_id": record.session_id,
                "stream_id": record.stream_id,
                "created_at": self._serialize_dt(record.created_at),
                "last_seen_at": self._serialize_dt(record.last_seen_at),
                "next_turn_id": str(record.next_turn_id),
                "user_id": record.user_id or "",
            },
        )
        self._redis.expire(key, self._ttl_seconds)

    def _load_record(self, cookie_token: str) -> SessionRecord | None:
        token_digest = digest_token(cookie_token)
        payload = self._redis.hgetall(self._key(token_digest))
        if not payload:
            return None
        return SessionRecord(
            cookie_token=cookie_token,
            token_digest=token_digest,
            session_id=str(payload["session_id"]),
            stream_id=str(payload["stream_id"]),
            created_at=self._parse_dt(str(payload["created_at"])),
            last_seen_at=self._parse_dt(str(payload["last_seen_at"])),
            next_turn_id=int(payload.get("next_turn_id") or 1),
            user_id=payload.get("user_id") or None,
        )

    def _touch(self, record: SessionRecord) -> None:
        now = self._now()
        record.last_seen_at = now
        key = self._key(record.token_digest)
        self._redis.hset(key, mapping={"last_seen_at": self._serialize_dt(now)})
        self._redis.expire(key, self._ttl_seconds)

    def _key(self, token_digest: str) -> str:
        return redis_store.key("session", token_digest)

    def _generate_session_id(self, now: datetime) -> str:
        return f"sess_{self._format_beijing_timestamp(now)}_{secrets.token_hex(16)}"

    def _generate_stream_id(self, now: datetime) -> str:
        return f"stream_{self._format_beijing_timestamp(now)}_{secrets.token_hex(8)}"

    @staticmethod
    def _format_beijing_timestamp(now: datetime) -> str:
        return now.astimezone(BEIJING_TZ).strftime("%Y%m%dT%H%M%SCST")

    @staticmethod
    def _serialize_dt(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value).astimezone(UTC)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)


session_service = SessionService(ttl_seconds=settings.session_ttl_seconds)
