"""Studio endpoints (architecture doc §19, §26.5).

MVP2 scope - structurally prepared per the implementation plan, but not
functionally implemented in the MVP1 core flow (upload -> embed -> chat).
Each endpoint reuses the same RAG building blocks (retrieval + Langdock)
once implemented; wire them up after the chat flow is stable.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/api/notebooks", tags=["studio"])


def _not_implemented(name: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Studio feature '{name}' is planned for MVP2, see docs/architecture.md §19",
    )


@router.post("/{notebook_id}/studio/summary")
async def studio_summary(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("summary")


@router.post("/{notebook_id}/studio/faq")
async def studio_faq(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("faq")


@router.post("/{notebook_id}/studio/timeline")
async def studio_timeline(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("timeline")


@router.post("/{notebook_id}/studio/briefing")
async def studio_briefing(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("briefing")


@router.post("/{notebook_id}/studio/audio-script")
async def studio_audio_script(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("audio-script")
