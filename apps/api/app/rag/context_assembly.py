"""Builds the LLM context block from retrieved chunks (architecture doc §16.4).

Qdrant only stores metadata in its payload, not the chunk text itself, so
this step re-fetches the actual text from Postgres (the source of truth)
before handing it to Sonnet.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.rag.retrieval import RetrievedChunk


async def fetch_chunk_texts(db: AsyncSession, chunk_ids: list[str]) -> dict[str, models.Chunk]:
    if not chunk_ids:
        return {}
    ids = [uuid.UUID(cid) for cid in chunk_ids]
    result = await db.execute(select(models.Chunk).where(models.Chunk.id.in_(ids)))
    return {str(chunk.id): chunk for chunk in result.scalars().all()}


def build_context_block(
    chunks: list[RetrievedChunk], texts_by_chunk_id: dict[str, models.Chunk]
) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        db_chunk = texts_by_chunk_id.get(chunk.chunk_id)
        if db_chunk is None:
            continue  # stale Qdrant point without a matching Postgres row - skip defensively
        pages = (
            f"{chunk.page_start}"
            if chunk.page_start is not None and chunk.page_start == chunk.page_end
            else f"{chunk.page_start}-{chunk.page_end}"
            if chunk.page_start is not None
            else "n/a"
        )
        blocks.append(
            "\n".join(
                [
                    f"[Quelle {index}]",
                    f"source_id: {chunk.source_id}",
                    f"chunk_id: {chunk.chunk_id}",
                    f"document_name: {chunk.document_name}",
                    f"page: {pages}",
                    f"heading: {chunk.heading or '-'}",
                    "text:",
                    db_chunk.text,
                ]
            )
        )
    return "\n\n".join(blocks)
