"""
Simple in-memory token-bucket rate limiter.
10 requests per 60 seconds per user.
"""
import time
import threading
from collections import defaultdict

_lock = threading.Lock()
_buckets: dict[str, dict] = defaultdict(lambda: {"tokens": 10, "last": time.monotonic()})

RATE = 10       # max tokens
REFILL = 10     # tokens/minute
WINDOW = 60.0   # seconds


def check_rate_limit(username: str) -> bool:
    """
    Returns True if the request is allowed, False if rate-limited.
    Refills tokens based on elapsed time (token-bucket algorithm).
    """
    with _lock:
        bucket = _buckets[username]
        now = time.monotonic()
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(RATE, bucket["tokens"] + elapsed * (REFILL / WINDOW))
        bucket["last"] = now
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False
