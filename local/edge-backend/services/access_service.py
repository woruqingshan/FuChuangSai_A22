from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from config import settings
from services.db import db_session
from services.db_models import InvitationCode
from services.security import digest_token, fingerprint_secret, new_opaque_token
from services.session_service import SessionRecord
from services.storage import redis_store


class AccessError(Exception):
    def __init__(self, detail: str, status_code: int = 403) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class InvitationCodeState:
    code: str
    enabled: bool = True
    expires_at: datetime | None = None
    max_uses: int | None = None


@dataclass
class AccessGrant:
    access_token: str
    session_id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class AccessService:
    def __init__(self) -> None:
        self._redis = redis_store.client
        self._codes = [code for code in (self._parse_code(raw_code) for raw_code in settings.invitation_codes) if code]

    def sync_invitation_codes(self) -> None:
        now = datetime.now(UTC)
        with db_session() as session:
            for code_state in self._codes:
                fingerprint = fingerprint_secret(code_state.code)
                existing = session.scalar(
                    select(InvitationCode).where(InvitationCode.code_fingerprint == fingerprint)
                )
                if existing:
                    existing.enabled = code_state.enabled
                    existing.expires_at = code_state.expires_at
                    existing.max_uses = code_state.max_uses
                    existing.updated_at = now
                    continue
                session.add(
                    InvitationCode(
                        code_fingerprint=fingerprint,
                        enabled=code_state.enabled,
                        expires_at=code_state.expires_at,
                        max_uses=code_state.max_uses,
                        used_count=0,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def has_configured_codes(self) -> bool:
        return bool(self._codes)

    def is_authorized(self, *, session: SessionRecord, access_token: str | None) -> bool:
        grant = self._get_valid_grant(access_token)
        if not grant or grant.session_id != session.session_id:
            return False
        self._touch_grant(access_token)
        return True

    def verify_code(
        self,
        *,
        session: SessionRecord,
        access_token: str | None,
        code: str,
    ) -> tuple[AccessGrant, str, bool]:
        existing_grant = self._get_valid_grant(access_token)
        if existing_grant and existing_grant.session_id == session.session_id:
            self._touch_grant(access_token)
            return existing_grant, access_token or "", False

        normalized_code = code.strip()
        if not normalized_code:
            raise AccessError("Invitation code is invalid or expired.", status_code=403)
        now = datetime.now(UTC)
        with db_session() as db:
            code_row = db.scalar(
                select(InvitationCode)
                .where(InvitationCode.code_fingerprint == fingerprint_secret(normalized_code))
                .with_for_update()
            )
            if not code_row or not self._code_is_usable(code_row, now):
                raise AccessError("Invitation code is invalid or expired.", status_code=403)
            code_row.used_count += 1
            code_row.updated_at = now

        token = new_opaque_token()
        grant = AccessGrant(
            access_token=token,
            session_id=session.session_id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(seconds=settings.access_ttl_seconds),
        )
        self._save_grant(grant)
        return grant, token, True

    def require_access(self, *, session: SessionRecord, access_token: str | None) -> AccessGrant:
        grant = self._get_valid_grant(access_token)
        if not grant or grant.session_id != session.session_id:
            raise AccessError("Invitation access is required.", status_code=403)
        self._touch_grant(access_token)
        return grant

    def _save_grant(self, grant: AccessGrant) -> None:
        key = self._key(digest_token(grant.access_token))
        self._redis.hset(
            key,
            mapping={
                "session_id": grant.session_id,
                "created_at": self._serialize_dt(grant.created_at),
                "last_seen_at": self._serialize_dt(grant.last_seen_at),
                "expires_at": self._serialize_dt(grant.expires_at),
            },
        )
        self._redis.expire(key, settings.access_ttl_seconds)

    def _get_valid_grant(self, access_token: str | None) -> AccessGrant | None:
        if not access_token:
            return None
        payload = self._redis.hgetall(self._key(digest_token(access_token)))
        if not payload:
            return None
        expires_at = self._parse_dt(str(payload["expires_at"]))
        if expires_at <= datetime.now(UTC):
            self._redis.delete(self._key(digest_token(access_token)))
            return None
        return AccessGrant(
            access_token=access_token,
            session_id=str(payload["session_id"]),
            created_at=self._parse_dt(str(payload["created_at"])),
            last_seen_at=self._parse_dt(str(payload["last_seen_at"])),
            expires_at=expires_at,
        )

    def _touch_grant(self, access_token: str | None) -> None:
        if not access_token:
            return
        key = self._key(digest_token(access_token))
        if self._redis.exists(key):
            self._redis.hset(key, mapping={"last_seen_at": self._serialize_dt(datetime.now(UTC))})
            self._redis.expire(key, settings.access_ttl_seconds)

    def _key(self, token_digest: str) -> str:
        return redis_store.key("access", token_digest)

    @staticmethod
    def _code_is_usable(code_row: InvitationCode, now: datetime) -> bool:
        if not code_row.enabled:
            return False
        if code_row.expires_at and code_row.expires_at <= now:
            return False
        if code_row.max_uses is not None and code_row.used_count >= code_row.max_uses:
            return False
        return True

    @staticmethod
    def _parse_code(raw_code: dict) -> InvitationCodeState | None:
        code = str(raw_code.get("code", "")).strip()
        if not code:
            return None
        enabled = bool(raw_code.get("enabled", True))
        expires_at = None
        expires_at_raw = str(raw_code.get("expires_at", "")).strip()
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00")).astimezone(UTC)
            except ValueError:
                expires_at = datetime.now(UTC) - timedelta(seconds=1)
        max_uses = raw_code.get("max_uses")
        try:
            parsed_max_uses = int(max_uses) if max_uses is not None else None
        except (TypeError, ValueError):
            parsed_max_uses = None
        if parsed_max_uses is not None and parsed_max_uses < 0:
            parsed_max_uses = 0
        return InvitationCodeState(
            code=code,
            enabled=enabled,
            expires_at=expires_at,
            max_uses=parsed_max_uses,
        )

    @staticmethod
    def _serialize_dt(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value).astimezone(UTC)


access_service = AccessService()
