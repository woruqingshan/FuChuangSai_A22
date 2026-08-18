from dataclasses import dataclass
from hashlib import sha256

from services.storage import redis_store


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._redis = redis_store.client

    def allow(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        redis_key = redis_store.key("rate", sha256(key.encode("utf-8")).hexdigest())
        count = int(self._redis.incr(redis_key))
        if count == 1:
            self._redis.expire(redis_key, window_seconds)
        if count <= limit:
            return RateLimitResult(allowed=True)
        ttl = self._redis.ttl(redis_key)
        retry_after = ttl if ttl and ttl > 0 else window_seconds
        return RateLimitResult(allowed=False, retry_after_seconds=max(1, int(retry_after)))

    def cleanup(self, *, max_age_seconds: int = 7200) -> int:
        return 0


rate_limiter = FixedWindowRateLimiter()
