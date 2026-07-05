from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthenticatedUser, get_current_user, get_db
from app.notebooks import service
from app.schemas.notebook import NotebookCreate, NotebookOut, NotebookUpdate

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


def _to_out(notebook, source_count: int = 0) -> NotebookOut:
    return NotebookOut(
        id=str(notebook.id),
        owner_id=str(notebook.owner_id),
        title=notebook.title,
        description=notebook.description,
        visibility=notebook.visibility,
        source_count=source_count,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
    )


@router.get("", response_model=list[NotebookOut])
async def list_notebooks(
    db: AsyncSession = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)
) -> list[NotebookOut]:
    rows = await service.list_notebooks(db, user.id)
    return [_to_out(notebook, count) for notebook, count in rows]


@router.post("", response_model=NotebookOut, status_code=201)
async def create_notebook(
    payload: NotebookCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NotebookOut:
    notebook = await service.create_notebook(db, user.id, payload)
    return _to_out(notebook)


@router.get("/{notebook_id}", response_model=NotebookOut)
async def get_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NotebookOut:
    notebook = await service.get_notebook_or_404(db, notebook_id)
    service.assert_can_access(notebook, user.id)
    return _to_out(notebook, len(notebook.sources))


@router.patch("/{notebook_id}", response_model=NotebookOut)
async def update_notebook(
    notebook_id: str,
    payload: NotebookUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NotebookOut:
    notebook = await service.get_notebook_or_404(db, notebook_id)
    service.assert_can_access(notebook, user.id)
    notebook = await service.update_notebook(db, notebook, payload)
    return _to_out(notebook)


@router.delete("/{notebook_id}", status_code=204)
async def delete_notebook(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    notebook = await service.get_notebook_or_404(db, notebook_id)
    service.assert_can_access(notebook, user.id)
    await service.delete_notebook(db, notebook)
