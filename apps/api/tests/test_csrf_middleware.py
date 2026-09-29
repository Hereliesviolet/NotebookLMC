"""Unit tests for the Double-Submit-Cookie CSRF middleware (Block 3).

Deliberately built against a minimal Starlette app rather than the full
FastAPI app: the middleware only inspects cookies/headers, so this avoids
pulling in Postgres/Redis/MinIO/Qdrant just to test it in isolation. The
full auth flow (login -> CSRF-protected write) is covered by the endpoint
tests in test_auth_endpoints.py.
"""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.middleware import CSRF_HEADER_NAME, CsrfMiddleware
from app.core.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME


async def _echo(request):
    return JSONResponse({"ok": True})


def _make_client() -> TestClient:
    app = Starlette(
        routes=[
            Route("/mutate", _echo, methods=["POST"]),
            Route("/read", _echo, methods=["GET"]),
        ],
        middleware=[],
    )
    app.add_middleware(CsrfMiddleware)
    return TestClient(app)


def test_post_without_session_cookie_is_allowed():
    # No session yet (e.g. /login itself) - nothing to protect.
    client = _make_client()
    response = client.post("/mutate")
    assert response.status_code == 200


def test_post_with_session_but_no_csrf_header_is_rejected():
    client = _make_client()
    client.cookies.set(SESSION_COOKIE_NAME, "some-session-id")
    client.cookies.set(CSRF_COOKIE_NAME, "the-real-token")
    response = client.post("/mutate")
    assert response.status_code == 403


def test_post_with_mismatched_csrf_header_is_rejected():
    client = _make_client()
    client.cookies.set(SESSION_COOKIE_NAME, "some-session-id")
    client.cookies.set(CSRF_COOKIE_NAME, "the-real-token")
    response = client.post("/mutate", headers={CSRF_HEADER_NAME: "wrong-token"})
    assert response.status_code == 403


def test_post_with_matching_csrf_header_is_allowed():
    client = _make_client()
    client.cookies.set(SESSION_COOKIE_NAME, "some-session-id")
    client.cookies.set(CSRF_COOKIE_NAME, "the-real-token")
    response = client.post("/mutate", headers={CSRF_HEADER_NAME: "the-real-token"})
    assert response.status_code == 200


def test_get_with_session_cookie_needs_no_csrf_header():
    client = _make_client()
    client.cookies.set(SESSION_COOKIE_NAME, "some-session-id")
    client.cookies.set(CSRF_COOKIE_NAME, "the-real-token")
    response = client.get("/read")
    assert response.status_code == 200
