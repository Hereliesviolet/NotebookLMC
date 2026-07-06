"""Authentication: Argon2 password hashing + cookie-based sessions.

`get_current_user` is the sole FastAPI dependency the rest of the app
relies on - everything else in this module (hashing, dev token stubs during
the ongoing migration) is an implementation detail behind it.
"""
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False

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
