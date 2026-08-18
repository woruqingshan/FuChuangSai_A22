from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets

from config import settings
from services.session_service import SessionRecord


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
    used_count: int = 0


@dataclass
class AccessGrant:
    access_token: str
    session_id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class AccessService:
    def __init__(self) -> None:
        self._codes = {
            code_state.code: code_state
            for code_state in (self._parse_code(raw_code) for raw_code in settings.invitation_codes)
            if code_state
        }
        self._grants_by_token: dict[str, AccessGrant] = {}

    def has_configured_codes(self) -> bool:
        return bool(self._codes)

    def is_authorized(self, *, session: SessionRecord, access_token: str | None) -> bool:
        grant = self._get_valid_grant(access_token)
        if not grant or grant.session_id != session.session_id:
            return False
        grant.last_seen_at = datetime.now(UTC)
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
            existing_grant.last_seen_at = datetime.now(UTC)
            return existing_grant, existing_grant.access_token, False

        code_state = self._codes.get(code.strip())
        if not code_state or not self._code_is_usable(code_state):
            raise AccessError("Invitation code is invalid or expired.", status_code=403)

        now = datetime.now(UTC)
        token = secrets.token_urlsafe(32)
        grant = AccessGrant(
            access_token=token,
            session_id=session.session_id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(seconds=settings.access_ttl_seconds),
        )
        self._grants_by_token[token] = grant
        code_state.used_count += 1
        self._cleanup_expired(now=now)
        return grant, token, True

    def require_access(self, *, session: SessionRecord, access_token: str | None) -> AccessGrant:
        grant = self._get_valid_grant(access_token)
        if not grant or grant.session_id != session.session_id:
            raise AccessError("Invitation access is required.", status_code=403)
        grant.last_seen_at = datetime.now(UTC)
        return grant

    def _get_valid_grant(self, access_token: str | None) -> AccessGrant | None:
        if not access_token:
            return None
        grant = self._grants_by_token.get(access_token)
        if not grant:
            return None
        now = datetime.now(UTC)
        if grant.expires_at <= now:
            self._grants_by_token.pop(access_token, None)
            return None
        return grant

    def _code_is_usable(self, code_state: InvitationCodeState) -> bool:
        now = datetime.now(UTC)
        if not code_state.enabled:
            return False
        if code_state.expires_at and code_state.expires_at <= now:
            return False
        if code_state.max_uses is not None and code_state.used_count >= code_state.max_uses:
            return False
        return True

    def _cleanup_expired(self, *, now: datetime) -> None:
        expired_tokens = [
            token for token, grant in self._grants_by_token.items() if grant.expires_at <= now
        ]
        for token in expired_tokens:
            self._grants_by_token.pop(token, None)

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


access_service = AccessService()
