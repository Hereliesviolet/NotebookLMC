"""End-to-end tests for /api/auth/* against the real FastAPI app.

Needs a real Postgres + Redis (no mocking) - CI provisions both as service
containers (see .github/workflows/pytest.yml). Locally this runs fine
inside the `api` container, which is already wired to the real
notebook-postgres/notebook-redis services via docker-compose.yml.

Each test uses a fresh, randomized email so the suite is safe to run
repeatedly against a persistent dev database without unique-constraint
collisions from previous runs.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_redis
from app.main import app

VALID_PASSWORD = "correct-horse-battery-staple"


def _unique_email() -> str:
    return f"pytest-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
async def client():
    # Register is rate-limited per IP only (no per-test email dimension to
    # isolate on, unlike login) - every test in this module hits it from the
    # same ASGI-transport "IP", so the counter must be reset between tests to
    # keep them independent. Scoped to just this key prefix rather than a
    # blanket FLUSHDB, since locally this Redis instance also backs real
    # sessions/queues.
    redis = get_redis()
    for key in redis.scan_iter("register_attempts:*"):
        redis.delete(key)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def test_register_returns_user_without_password(client: AsyncClient):
    email = _unique_email()
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "name": "Pytest User"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_is_rejected(client: AsyncClient):
    email = _unique_email()
    payload = {"email": email, "password": VALID_PASSWORD, "name": "Pytest User"}
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


async def test_register_rejects_too_short_password(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": _unique_email(), "password": "short", "name": "Pytest User"},
    )
    assert response.status_code == 422


async def test_login_with_wrong_password_returns_generic_401(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )

    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_with_unknown_email_returns_generic_401(client: AsyncClient):
    response = await client.post(
        "/api/auth/login", json={"email": _unique_email(), "password": VALID_PASSWORD}
    )
    assert response.status_code == 401


async def test_login_success_sets_session_and_csrf_cookies(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )

    response = await client.post(
        "/api/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert client.cookies.get("session_id") is not None
    assert client.cookies.get("csrf_token") is not None


async def test_me_requires_valid_session(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user_after_login(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )
    await client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})

    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == email


async def test_mutating_request_without_csrf_header_is_rejected(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )
    await client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})

    response = await client.post("/api/notebooks", json={"title": "No CSRF header"})
    assert response.status_code == 403


async def test_mutating_request_with_correct_csrf_header_succeeds(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )
    await client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    csrf_token = client.cookies.get("csrf_token")

    response = await client.post(
        "/api/notebooks", json={"title": "With CSRF header"}, headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 201

    notebook_id = response.json()["id"]
    cleanup = await client.delete(
        f"/api/notebooks/{notebook_id}", headers={"X-CSRF-Token": csrf_token}
    )
    assert cleanup.status_code == 204


async def test_logout_invalidates_session(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )
    await client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})

    # Logout is itself CSRF-protected (POST + session cookie) - a bare POST
    # without the header is correctly rejected, covered separately by
    # test_mutating_request_without_csrf_header_is_rejected.
    csrf_token = client.cookies.get("csrf_token")
    logout_response = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_response.status_code == 200

    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 401


async def test_login_rate_limit_blocks_after_five_attempts_per_minute(client: AsyncClient):
    email = _unique_email()
    await client.post(
        "/api/auth/register", json={"email": email, "password": VALID_PASSWORD, "name": "X"}
    )

    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"email": email, "password": "wrong-password"}
        )
        assert response.status_code == 401

    blocked_response = await client.post(
        "/api/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert blocked_response.status_code == 429
    assert "Retry-After" in blocked_response.headers

    # Even the correct password is blocked once the rate limit is hit.
    still_blocked = await client.post(
        "/api/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert still_blocked.status_code == 429


async def test_register_rate_limit_blocks_after_five_attempts_per_ip(client: AsyncClient):
    # Distinct emails per attempt - register rejects duplicates with 409
    # before the rate limit check would otherwise matter, so re-using one
    # email would make this a duplicate-email test, not a rate-limit test.
    for _ in range(5):
        response = await client.post(
            "/api/auth/register",
            json={"email": _unique_email(), "password": VALID_PASSWORD, "name": "X"},
        )
        assert response.status_code == 201

    blocked_response = await client.post(
        "/api/auth/register",
        json={"email": _unique_email(), "password": VALID_PASSWORD, "name": "X"},
    )
    assert blocked_response.status_code == 429
    assert "Retry-After" in blocked_response.headers
