from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.core.security import AuthenticatedUser, issue_dev_token
from app.db import models
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Dev/demo login (architecture doc §21.1).

    Returns a static bearer token for the single demo user. Any email in the
    request body is ignored for now - this exists purely so the frontend has
    a stable login call to make while real auth is pending.
    """
    settings = get_settings()
    email = payload.email or settings.dev_demo_user_email

    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = models.User(email=email, name=settings.dev_demo_user_name, role="owner")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return LoginResponse(access_token=issue_dev_token(str(user.id)))


@router.post("/logout")
async def logout() -> dict:
    # Stateless dev tokens - nothing to invalidate server-side yet.
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)
