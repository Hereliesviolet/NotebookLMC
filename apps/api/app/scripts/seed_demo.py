"""Seeds the demo user and an empty demo notebook for local development.

Run via `make seed` (executes inside the api container).
"""
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.db import models
from app.db.session import AsyncSessionLocal


async def main() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.User).where(models.User.email == settings.dev_demo_user_email))
        user = result.scalar_one_or_none()
        if user is None:
            user = models.User(email=settings.dev_demo_user_email, name=settings.dev_demo_user_name, role="owner")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created demo user {user.email} ({user.id})")
        else:
            print(f"Demo user already exists: {user.email} ({user.id})")

        result = await db.execute(select(models.Notebook).where(models.Notebook.owner_id == user.id))
        notebook = result.scalars().first()
        if notebook is None:
            notebook = models.Notebook(
                owner_id=user.id,
                title="Demo Notebook",
                description="Seeded demo notebook - upload a source to get started.",
                visibility="private",
            )
            db.add(notebook)
            await db.commit()
            await db.refresh(notebook)
            print(f"Created demo notebook {notebook.title} ({notebook.id})")
        else:
            print(f"Demo notebook already exists: {notebook.title} ({notebook.id})")

        from app.core.security import issue_dev_token

        print(f"\nDev bearer token: {issue_dev_token(str(user.id))}")


if __name__ == "__main__":
    asyncio.run(main())
