import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthenticatedUser, get_current_user, get_db
from app.db import models
from app.notebooks import service as notebooks_service
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(tags=["notes"])


def _to_out(note: models.Note) -> NoteOut:
    return NoteOut(
        id=str(note.id),
        notebook_id=str(note.notebook_id),
        title=note.title,
        content=note.content,
        source_refs_json=note.source_refs_json,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/api/notebooks/{notebook_id}/notes", response_model=list[NoteOut])
async def list_notes(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[NoteOut]:
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)
    result = await db.execute(
        select(models.Note)
        .where(models.Note.notebook_id == notebook_id)
        .order_by(models.Note.created_at.desc())
    )
    return [_to_out(n) for n in result.scalars().all()]


@router.post("/api/notebooks/{notebook_id}/notes", response_model=NoteOut, status_code=201)
async def create_note(
    notebook_id: str,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NoteOut:
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)
    note = models.Note(
        notebook_id=notebook.id,
        created_by=user.id,
        title=payload.title,
        content=payload.content,
        source_refs_json=payload.source_refs_json,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _to_out(note)


async def _get_note_or_404(db: AsyncSession, note_id: str) -> models.Note:
    try:
        note_uuid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    note = await db.get(models.Note, note_uuid)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.patch("/api/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    notebook = await notebooks_service.get_notebook_or_404(db, str(note.notebook_id))
    notebooks_service.assert_can_access(notebook, user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return _to_out(note)


@router.delete("/api/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    note = await _get_note_or_404(db, note_id)
    notebook = await notebooks_service.get_notebook_or_404(db, str(note.notebook_id))
    notebooks_service.assert_can_access(notebook, user.id)
    await db.delete(note)
    await db.commit()
