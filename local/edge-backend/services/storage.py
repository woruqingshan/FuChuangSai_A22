from __future__ import annotations

import redis

from config import settings


class StorageUnavailableError(Exception):
    pass


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class RedisStore:
    def __init__(self) -> None:
        self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    @property
    def client(self) -> redis.Redis:
        return self._client

    def key(self, *parts: str) -> str:
        return ":".join([settings.redis_key_prefix, *parts])

    def ping(self) -> None:
        try:
            self._client.ping()
        except redis.RedisError as exc:
            raise StorageUnavailableError("Redis is unavailable.") from exc


redis_store = RedisStore()
