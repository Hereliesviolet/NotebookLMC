from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat import service
from app.core.deps import AuthenticatedUser, get_current_user, get_db
from app.db import models
from app.notebooks import service as notebooks_service
from app.schemas.chat import ChatRequest, ChatResponse, MessageOut

router = APIRouter(prefix="/api/notebooks", tags=["chat"])


@router.get("/{notebook_id}/messages", response_model=list[MessageOut])
async def list_messages(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[MessageOut]:
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)
    result = await db.execute(
        select(models.Message)
        .where(models.Message.notebook_id == notebook_id)
        .order_by(models.Message.created_at.asc())
    )
    return [
        MessageOut(
            id=str(m.id),
            notebook_id=str(m.notebook_id),
            role=m.role,
            content=m.content,
            model=m.model,
            citations_json=m.citations_json,
            created_at=m.created_at,
        )
        for m in result.scalars().all()
    ]


@router.post("/{notebook_id}/chat", response_model=ChatResponse)
async def chat(
    notebook_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChatResponse:
    """RAG chat endpoint - full flow, see
    docs/rag-pipeline.md: intent detection -> query rewrite -> embedding ->
    Qdrant retrieval -> context assembly -> Sonnet -> citation validation.
    """
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)
    return await service.answer_question(
        db, notebook_id=notebook_id, user_id=user.id, payload=payload
    )
