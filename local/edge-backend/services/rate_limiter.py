from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[datetime, int]] = {}

    def allow(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        now = datetime.now(UTC)
        window_started_at, count = self._windows.get(key, (now, 0))
        elapsed = (now - window_started_at).total_seconds()
        if elapsed >= window_seconds:
            self._windows[key] = (now, 1)
            return RateLimitResult(allowed=True)
        if count >= limit:
            retry_after = max(1, int(window_seconds - elapsed))
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
        self._windows[key] = (window_started_at, count + 1)
        return RateLimitResult(allowed=True)

    def cleanup(self, *, max_age_seconds: int = 7200) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
        stale_keys = [key for key, (started_at, _count) in self._windows.items() if started_at < cutoff]
        for key in stale_keys:
            self._windows.pop(key, None)
        return len(stale_keys)


rate_limiter = FixedWindowRateLimiter()
