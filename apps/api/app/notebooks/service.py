import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas.notebook import NotebookCreate, NotebookUpdate


async def list_notebooks(db: AsyncSession, owner_id: str) -> list[tuple[models.Notebook, int]]:
    stmt = (
        select(models.Notebook, func.count(models.Source.id))
        .outerjoin(models.Source, models.Source.notebook_id == models.Notebook.id)
        .where(models.Notebook.owner_id == owner_id)
        .group_by(models.Notebook.id)
        .order_by(models.Notebook.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.all())


async def count_sources(db: AsyncSession, notebook_id: str) -> int:
    """Counts sources via a query instead of `notebook.sources` - the lazy
    relationship can't be accessed on an AsyncSession without an explicit
    (e.g. selectinload) eager load and would raise MissingGreenlet otherwise.
    """
    stmt = select(func.count(models.Source.id)).where(models.Source.notebook_id == notebook_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_notebook_or_404(db: AsyncSession, notebook_id: str) -> models.Notebook:
    try:
        notebook_uuid = uuid.UUID(notebook_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    notebook = await db.get(models.Notebook, notebook_uuid)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook


def assert_can_access(notebook: models.Notebook, user_id: str) -> None:
    """MVP access check: owner-only. Sharing/roles (§21.3) land in MVP3."""
    if str(notebook.owner_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this notebook")


async def create_notebook(db: AsyncSession, owner_id: str, payload: NotebookCreate) -> models.Notebook:
    notebook = models.Notebook(
        owner_id=owner_id,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
    )
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)
    return notebook


async def update_notebook(db: AsyncSession, notebook: models.Notebook, payload: NotebookUpdate) -> models.Notebook:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(notebook, field, value)
    await db.commit()
    await db.refresh(notebook)
    return notebook


async def delete_notebook(db: AsyncSession, notebook: models.Notebook) -> None:
    await db.delete(notebook)
    await db.commit()
