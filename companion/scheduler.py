import random
from datetime import datetime, timedelta, timezone


def next_check_at(seconds_remaining: int, jitter_seconds: int = 90, now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    jitter = random.randint(15, max(15, jitter_seconds))
    return current + timedelta(seconds=max(0, seconds_remaining) + jitter)


def backoff_seconds(attempt: int, maximum: int = 3600) -> int:
    return min(maximum, 30 * (2 ** max(0, attempt)))
