"""Notebook-wide context assembly for Studio artifacts (summary/faq/timeline/
briefing, architecture doc §19). Unlike chat/service.py's query-based
retrieval, Studio needs a representative sample of every indexed source, not
the chunks most similar to a specific question - so this reads Postgres
directly ordered by chunk_index instead of doing a Qdrant vector search.
"""
import uuid
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import models
from app.rag.context_assembly import build_context_block
from app.rag.retrieval import RetrievedChunk

MIN_PER_SOURCE_CHAR_BUDGET = 2000


async def fetch_indexed_sources(
    db: AsyncSession, notebook_id: str, source_ids: list[str] | None = None
) -> list[models.Source]:
    stmt = select(models.Source).where(models.Source.notebook_id == notebook_id, models.Source.status == "indexed")
    if source_ids:
        stmt = stmt.where(models.Source.id.in_([uuid.UUID(s) for s in source_ids]))
    stmt = stmt.order_by(models.Source.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def build_notebook_wide_context(
    db: AsyncSession,
    notebook_id: str,
    source_ids: list[str] | None = None,
    max_chunks_per_source: int | None = None,
    max_total_chars: int | None = None,
) -> tuple[str, list[models.Source]]:
    """Diversity-first context: an equal character budget per source (no
    query/vector score exists here to rank by), so a handful of very large
    sources can't crowd out small ones - same diversity principle as the
    chat-retrieval fix, just applied on the chunk_index axis instead of
    vector score.
    """
    settings = get_settings()
    max_chunks_per_source = max_chunks_per_source or settings.studio_max_chunks_per_source
    max_total_chars = max_total_chars or settings.studio_max_context_chars

    sources = await fetch_indexed_sources(db, notebook_id, source_ids)
    if not sources:
        return "", []

    per_source_budget = max(max_total_chars // len(sources), MIN_PER_SOURCE_CHAR_BUDGET)

    selected_chunks: list[RetrievedChunk] = []
    texts_by_chunk_id: dict[str, SimpleNamespace] = {}
    for source in sources:
        result = await db.execute(
            select(models.Chunk)
            .where(models.Chunk.source_id == source.id)
            .order_by(models.Chunk.chunk_index.asc())
            .limit(max_chunks_per_source)
        )
        used_chars = 0
        for chunk in result.scalars().all():
            remaining = per_source_budget - used_chars
            if remaining <= 0:
                break
            text = chunk.text
            if len(text) > remaining:
                text = text[:remaining].rstrip() + " […gekürzt]"
            used_chars += len(text)

            chunk_id = str(chunk.id)
            texts_by_chunk_id[chunk_id] = SimpleNamespace(text=text)
            selected_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    score=0.0,
                    source_id=str(source.id),
                    document_name=source.original_filename,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    heading=chunk.heading,
                    chunk_type=chunk.chunk_type,
                )
            )
            if len(chunk.text) > remaining:
                break  # budget exhausted for this source, further chunks would only be cut to nothing

    context = build_context_block(selected_chunks, texts_by_chunk_id)
    return context, sources
