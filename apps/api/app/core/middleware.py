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
from starlette.responses import Response


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.headers.get("access-control-request-private-network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response
