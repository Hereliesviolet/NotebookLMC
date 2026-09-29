"""Redis-backed server-side sessions (see docs/security.md).

A session is just an opaque, unguessable id (`secrets.token_urlsafe(32)`)
mapped to a user id in Redis with a sliding TTL - every read extends the
TTL, so an active user never gets logged out mid-session, while an
abandoned session still expires.
"""

import secrets

from redis import Redis

from app.core.config import get_settings

SESSION_KEY_PREFIX = "session:"


def create_session(redis: Redis, user_id: str) -> str:
    settings = get_settings()
    session_id = secrets.token_urlsafe(32)
    redis.set(f"{SESSION_KEY_PREFIX}{session_id}", user_id, ex=settings.session_ttl_seconds)
    return session_id


def get_session(redis: Redis, session_id: str) -> str | None:
    settings = get_settings()
    key = f"{SESSION_KEY_PREFIX}{session_id}"
    user_id = redis.get(key)
    if user_id is None:
        return None
    redis.expire(key, settings.session_ttl_seconds)
    return user_id.decode() if isinstance(user_id, bytes) else user_id


def destroy_session(redis: Redis, session_id: str) -> None:
    redis.delete(f"{SESSION_KEY_PREFIX}{session_id}")
