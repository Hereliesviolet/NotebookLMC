"""Dev/demo authentication (architecture doc §21.1).

This is intentionally a stub: a single demo user gets a static, opaque
bearer token. It exists so the rest of the app can depend on
`get_current_user` without caring how auth actually works. Swapping this
for real auth (Entra ID / SSO, §21.2) later only means replacing the
functions in this file - no other module needs to change.
"""
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

DEV_TOKEN_PREFIX = "dev:"


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    name: str
    role: str = "owner"


def issue_dev_token(user_id: str) -> str:
    return f"{DEV_TOKEN_PREFIX}{user_id}"


def parse_dev_token(token: str) -> str | None:
    if not token.startswith(DEV_TOKEN_PREFIX):
        return None
    return token[len(DEV_TOKEN_PREFIX):]


def extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


async def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency resolving the current user from the demo token.

    TODO(auth): replace with real session/JWT validation once SSO (Entra ID)
    is wired up. Callers only rely on this function's return type, so the
    swap is isolated to this file.
    """
    settings = get_settings()
    if not settings.dev_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Only dev/demo auth is implemented so far.",
        )

    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    user_id = parse_dev_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    from app.db.session import AsyncSessionLocal
    from app.db import models

    async with AsyncSessionLocal() as session:
        user = await session.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
        return AuthenticatedUser(id=str(user.id), email=user.email, name=user.name, role=user.role)
