import fakeredis

from app.core.sessions import create_session, destroy_session, get_session


def _redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


def test_create_session_returns_opaque_id_and_stores_user_id():
    redis = _redis()
    session_id = create_session(redis, "user-123")

    assert isinstance(session_id, str)
    assert len(session_id) > 20
    assert get_session(redis, session_id) == "user-123"


def test_get_session_returns_none_for_unknown_session():
    redis = _redis()
    assert get_session(redis, "does-not-exist") is None


def test_get_session_extends_ttl_on_read():
    redis = _redis()
    session_id = create_session(redis, "user-123")
    key = f"session:{session_id}"

    redis.expire(key, 5)
    assert redis.ttl(key) <= 5

    get_session(redis, session_id)
    assert redis.ttl(key) > 5


def test_destroy_session_invalidates_it():
    redis = _redis()
    session_id = create_session(redis, "user-123")

    destroy_session(redis, session_id)

    assert get_session(redis, session_id) is None


def test_destroy_session_on_unknown_id_is_a_noop():
    redis = _redis()
    destroy_session(redis, "does-not-exist")  # must not raise
