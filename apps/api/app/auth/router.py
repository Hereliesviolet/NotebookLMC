from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db, get_redis
from app.core.rate_limit import check_login_rate_limit, check_register_rate_limit
from app.core.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    AuthenticatedUser,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.core.sessions import create_session, destroy_session
from app.db import models
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookies(response: Response, session_id: str, csrf_token: str) -> None:
    settings = get_settings()
    cookie_kwargs = dict(
        secure=settings.session_cookie_secure,
        samesite="lax",
        domain=settings.session_cookie_domain or None,
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    response.set_cookie(SESSION_COOKIE_NAME, session_id, httponly=True, **cookie_kwargs)
    response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=False, **cookie_kwargs)


def _clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", domain=settings.session_cookie_domain or None)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", domain=settings.session_cookie_domain or None)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = check_register_rate_limit(redis, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts",
            headers={"Retry-After": str(retry_after)},
        )

    settings = get_settings()
    if len(payload.password) < settings.min_password_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {settings.min_password_length} characters",
        )

    result = await db.execute(select(models.User).where(models.User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = models.User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut(id=str(user.id), email=user.email, name=user.name, role=user.role)


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = check_login_rate_limit(redis, client_ip, payload.email)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    result = await db.execute(select(models.User).where(models.User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session_id = create_session(redis, str(user.id))
    _set_session_cookies(response, session_id, generate_csrf_token())
    return UserOut(id=str(user.id), email=user.email, name=user.name, role=user.role)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
) -> dict:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        destroy_session(redis, session_id)
    _clear_session_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)
