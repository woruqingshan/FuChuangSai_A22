from __future__ import annotations

from hashlib import sha256
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError


_password_hasher = PasswordHasher()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def fingerprint_secret(secret: str) -> str:
    normalized = secret.strip()
    return sha256(normalized.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def normalize_username(username: str) -> str:
    return " ".join(username.strip().lower().split())
