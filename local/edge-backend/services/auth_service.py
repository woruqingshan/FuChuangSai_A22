from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from config import settings
from services.db import db_session
from services.db_models import Account, User
from services.security import (
    digest_token,
    hash_password,
    new_opaque_token,
    normalize_username,
    verify_password,
)
from services.storage import redis_store


class AuthError(Exception):
    def __init__(self, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class AuthSession:
    user_id: str
    account_id: str
    username: str
    created_at: datetime
    last_seen_at: datetime


class AuthService:
    def __init__(self) -> None:
        self._redis = redis_store.client

    def register(self, *, username: str, password: str) -> tuple[AuthSession, str]:
        display_username, username_normalized = self._validate_username(username)
        self._validate_password(password)
        now = datetime.now(UTC)
        with db_session() as session:
            existing = session.scalar(select(Account).where(Account.username_normalized == username_normalized))
            if existing:
                raise AuthError("Username is already registered.", status_code=409)
            user = User(status="active", created_at=now, updated_at=now)
            account = Account(
                user=user,
                username=display_username,
                username_normalized=username_normalized,
                password_hash=hash_password(password),
                status="active",
                created_at=now,
                last_login_at=now,
            )
            session.add(user)
            session.add(account)
            session.flush()
            auth_session, token = self._create_auth_session(
                user_id=user.user_id,
                account_id=account.account_id,
                username=account.username,
            )
        return auth_session, token

    def login(self, *, username: str, password: str) -> tuple[AuthSession, str]:
        _display_username, username_normalized = self._validate_username(username)
        self._validate_password(password)
        with db_session() as session:
            account = session.scalar(select(Account).where(Account.username_normalized == username_normalized))
            if not account or account.status != "active" or not verify_password(account.password_hash, password):
                raise AuthError("用户名或密码错误", status_code=401)
            account.last_login_at = datetime.now(UTC)
            auth_session, token = self._create_auth_session(
                user_id=account.user_id,
                account_id=account.account_id,
                username=account.username,
            )
        return auth_session, token

    def resolve(self, auth_token: str | None) -> AuthSession | None:
        if not auth_token:
            return None
        key = self._key(digest_token(auth_token))
        payload = self._redis.hgetall(key)
        if not payload:
            return None
        auth_session = AuthSession(
            user_id=str(payload["user_id"]),
            account_id=str(payload["account_id"]),
            username=str(payload["username"]),
            created_at=self._parse_dt(str(payload["created_at"])),
            last_seen_at=datetime.now(UTC),
        )
        self._redis.hset(key, mapping={"last_seen_at": self._serialize_dt(auth_session.last_seen_at)})
        self._redis.expire(key, settings.auth_ttl_seconds)
        return auth_session

    def logout(self, auth_token: str | None) -> None:
        if auth_token:
            self._redis.delete(self._key(digest_token(auth_token)))

    def _create_auth_session(self, *, user_id: str, account_id: str, username: str) -> tuple[AuthSession, str]:
        now = datetime.now(UTC)
        token = new_opaque_token()
        auth_session = AuthSession(
            user_id=user_id,
            account_id=account_id,
            username=username,
            created_at=now,
            last_seen_at=now,
        )
        self._redis.hset(
            self._key(digest_token(token)),
            mapping={
                "user_id": user_id,
                "account_id": account_id,
                "username": username,
                "created_at": self._serialize_dt(now),
                "last_seen_at": self._serialize_dt(now),
            },
        )
        self._redis.expire(self._key(digest_token(token)), settings.auth_ttl_seconds)
        return auth_session, token

    @staticmethod
    def _validate_username(username: str) -> tuple[str, str]:
        display_username = " ".join(username.strip().split())
        username_normalized = normalize_username(username)
        if len(display_username) < 3 or len(display_username) > 80:
            raise AuthError("用户名长度需要在 3 到 80 个字符之间。", status_code=400)
        return display_username, username_normalized

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8 or len(password) > 128:
            raise AuthError("密码长度需要在 8 到 128 个字符之间。", status_code=400)

    def _key(self, token_digest: str) -> str:
        return redis_store.key("auth", token_digest)

    @staticmethod
    def _serialize_dt(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value).astimezone(UTC)


auth_service = AuthService()
