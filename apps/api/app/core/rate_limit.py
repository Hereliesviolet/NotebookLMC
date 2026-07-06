"""Fixed-window Redis rate limiter for login attempts.

Deliberately not a general-purpose limiter (no `slowapi`/new dependency) -
just the one counter the auth endpoints need: `INCR` + `EXPIRE` on a
per-(ip, email) key, reset every window.
"""
from redis import Redis

LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5


def check_login_rate_limit(redis: Redis, ip: str, email: str) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Increments the counter as a side effect."""
    key = f"login_attempts:{ip}:{email}"
    attempts = redis.incr(key)
    if attempts == 1:
        redis.expire(key, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    if attempts > LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        ttl = redis.ttl(key)
        return False, ttl if ttl and ttl > 0 else LOGIN_RATE_LIMIT_WINDOW_SECONDS
    return True, 0
