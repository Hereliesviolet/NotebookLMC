"""Chrome's Private Network Access (PNA) preflight check.

Cross-origin requests that Chrome classifies as going to a "more private"
address space (this can trigger even for localhost:3000 -> localhost:8000,
depending on the browser's sandbox/address-space configuration) carry an
extra preflight header `Access-Control-Request-Private-Network: true`.
Starlette's CORSMiddleware has no built-in support for answering this, so
without the matching `Access-Control-Allow-Private-Network: true` response
header the browser silently drops the real request client-side
(`TypeError: Failed to fetch`) - the server itself never sees anything wrong,
which is why curl/direct HTTP calls are unaffected.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.headers.get("access-control-request-private-network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """Double-Submit-Cookie CSRF protection.

    Only kicks in for requests that actually carry a session cookie - the
    login/register/logout endpoints themselves have nothing to protect (no
    session exists yet, or the session is being destroyed anyway), so no
    path allowlist is needed: an attacker without a valid session cookie
    can't reach anything worth protecting in the first place.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in CSRF_PROTECTED_METHODS and request.cookies.get(SESSION_COOKIE_NAME):
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if not cookie_token or not header_token or cookie_token != header_token:
                return JSONResponse(
                    status_code=403, content={"detail": "CSRF token missing or invalid"}
                )
        return await call_next(request)
