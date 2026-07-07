"""Fixed-window Redis rate limiter for auth endpoints.

Deliberately not a general-purpose limiter (no `slowapi`/new dependency) -
just the counters the auth endpoints need: `INCR` + `EXPIRE` on a
fixed key per identifier, reset every window.
"""
from redis import Redis

LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5

# Registration is rate-limited by IP only (no account exists yet to key a
# second dimension off) and uses a longer window with the same max attempts:
# registration is far rarer than login, so 5 attempts/5min is already tight
# for a legitimate user while still bounding fake-account creation.
REGISTER_RATE_LIMIT_WINDOW_SECONDS = 300
REGISTER_RATE_LIMIT_MAX_ATTEMPTS = 5


def check_rate_limit(
    redis: Redis, key_prefix: str, identifier: str, max_attempts: int, window_seconds: int
) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Increments the counter as a side effect."""
    key = f"{key_prefix}:{identifier}"
    attempts = redis.incr(key)
    if attempts == 1:
        redis.expire(key, window_seconds)
    if attempts > max_attempts:
        ttl = redis.ttl(key)
        return False, ttl if ttl and ttl > 0 else window_seconds
    return True, 0


def check_login_rate_limit(redis: Redis, ip: str, email: str) -> tuple[bool, int]:
    return check_rate_limit(
        redis,
        "login_attempts",
        f"{ip}:{email}",
        LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )


def check_register_rate_limit(redis: Redis, ip: str) -> tuple[bool, int]:
    return check_rate_limit(
        redis,
        "register_attempts",
        ip,
        REGISTER_RATE_LIMIT_MAX_ATTEMPTS,
        REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )
