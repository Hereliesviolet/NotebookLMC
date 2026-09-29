"""Self-hosted citation validation.

Never trust the LLM's citations blindly: check that every cited
source_id/chunk_id actually exists, belongs to this notebook, and that any
claimed page numbers are plausible. Unknown/hallucinated citations are
dropped rather than blocking the whole answer.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas.chat import Citation

VALID_CONFIDENCE = {"low", "medium", "high"}


async def validate_citations(
    db: AsyncSession, notebook_id: str, raw_citations: list[dict]
) -> list[Citation]:
    chunk_ids: list[uuid.UUID] = []
    for c in raw_citations:
        chunk_id = c.get("chunk_id")
        if not chunk_id:
            continue
        try:
            chunk_ids.append(uuid.UUID(chunk_id))
        except ValueError:
            continue  # not even a valid UUID - definitely not a real chunk

    known_chunks: dict[str, models.Chunk] = {}
    if chunk_ids:
        result = await db.execute(
            select(models.Chunk).where(
                models.Chunk.id.in_(chunk_ids), models.Chunk.notebook_id == notebook_id
            )
        )
        known_chunks = {str(chunk.id): chunk for chunk in result.scalars().all()}

    source_ids = {str(chunk.source_id) for chunk in known_chunks.values()}
    known_sources: dict[str, models.Source] = {}
    if source_ids:
        result = await db.execute(
            select(models.Source).where(models.Source.id.in_([uuid.UUID(s) for s in source_ids]))
        )
        known_sources = {str(source.id): source for source in result.scalars().all()}

    validated: list[Citation] = []
    for c in raw_citations:
        chunk_id = c.get("chunk_id")
        chunk = known_chunks.get(chunk_id) if chunk_id else None
        if chunk is None:
            continue  # hallucinated / cross-notebook chunk_id - drop silently

        source = known_sources.get(str(chunk.source_id))
        if source is None or str(source.notebook_id) != str(notebook_id):
            continue  # notebook/access mismatch - drop

        page_start = c.get("page_start")
        page_end = c.get("page_end")
        if (
            source.page_count is not None
            and page_start is not None
            and page_start > source.page_count
        ):
            page_start = None
            page_end = None

        validated.append(
            Citation(
                source_id=str(source.id),
                chunk_id=str(chunk.id),
                document_name=source.original_filename,
                page_start=page_start if page_start is not None else chunk.page_start,
                page_end=page_end if page_end is not None else chunk.page_end,
                quote=str(c.get("quote", ""))[:1000],
                supports_claim=c.get("supports_claim"),
            )
        )

    return validated


def downgrade_confidence_if_unsupported(confidence: str, citation_count: int) -> str:
    """If the model claims an answer but nothing survived validation, we
    can't trust it - forcibly downgrade rather than presenting a
    fully-confident, unsupported answer.
    """
    if confidence not in VALID_CONFIDENCE:
        confidence = "medium"
    if citation_count == 0 and confidence != "low":
        return "low"
    return confidence
