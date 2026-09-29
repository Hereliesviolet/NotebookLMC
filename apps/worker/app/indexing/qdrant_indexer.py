"""Qdrant upsert for chunk embeddings (architecture doc §15).

Payload shape matches the doc exactly:
  notebook_id, source_id, chunk_id, document_name, page_start, page_end,
  heading, chunk_type, created_at
"""

from datetime import datetime, timezone

from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import get_logger
from app.parsing.sanitize import sanitize_text
from app.qdrant.client import ensure_collection, get_qdrant_client

logger = get_logger(__name__)

# Qdrant rejects HTTP request bodies above ~32MB (see qdrant_client.http.exceptions.
# UnexpectedResponse "JSON payload ... is larger than allowed"). A single upsert
# for a large source (many chunks x 1536-dim vectors) can exceed that easily, so
# upserts are sent in bounded batches - well below the limit even for long chunks.
_UPSERT_BATCH_SIZE = 200


def index_chunks(
    notebook_id: str, source_id: str, document_name: str, chunks: list, vectors: list[list[float]]
) -> list[str]:
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunk/vector count mismatch: {len(chunks)} chunks vs {len(vectors)} vectors"
        )
    if not chunks:
        return []

    settings = get_settings()
    client = get_qdrant_client()
    ensure_collection(client)

    document_name = sanitize_text(document_name)
    points: list[qmodels.PointStruct] = []
    point_ids: list[str] = []

    for chunk, vector in zip(chunks, vectors):
        point_id = str(chunk.id)
        point_ids.append(point_id)
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "notebook_id": notebook_id,
                    "source_id": source_id,
                    "chunk_id": point_id,
                    "document_name": document_name,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "heading": chunk.heading,
                    "chunk_type": chunk.chunk_type,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

    for start in range(0, len(points), _UPSERT_BATCH_SIZE):
        batch = points[start : start + _UPSERT_BATCH_SIZE]
        client.upsert(collection_name=settings.qdrant_collection, points=batch, wait=True)

    logger.info("indexed %d chunks into qdrant for source %s", len(points), source_id)
    return point_ids
