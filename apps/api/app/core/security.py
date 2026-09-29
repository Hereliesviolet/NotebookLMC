"""Authentication: Argon2 password hashing + cookie-based Redis sessions.

`get_current_user` is the sole FastAPI dependency the rest of the app relies
on - callers only care about its `AuthenticatedUser` return type, so any
future auth change (e.g. SSO) is isolated to this file.
"""

import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status

SESSION_COOKIE_NAME = "session_id"
CSRF_COOKIE_NAME = "csrf_token"

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    name: str
    role: str = "owner"


async def get_current_user(request: Request) -> AuthenticatedUser:
    from app.core.sessions import get_session
    from app.db import models
    from app.db.session import AsyncSessionLocal
    from app.jobs.queue import get_redis_connection

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = get_session(get_redis_connection(), session_id)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    async with AsyncSessionLocal() as session:
        user = await session.get(models.User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
        return AuthenticatedUser(id=str(user.id), email=user.email, name=user.name, role=user.role)
