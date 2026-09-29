"""Qdrant client wrapper.

Collection design per architecture doc §15:
  - collection: notebook_chunks
  - vector size: 1536 (text-embedding-ada-002 via Langdock)
  - distance: cosine
  - payload: notebook_id, source_id, chunk_id, document_name, page_start,
    page_end, heading, chunk_type, created_at
"""

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(client: QdrantClient | None = None) -> None:
    """Idempotently create the notebook_chunks collection if it doesn't exist yet."""
    settings = get_settings()
    client = client or get_qdrant_client()

    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        return

    logger.info(
        "Creating Qdrant collection '%s' (size=%s, distance=cosine)",
        settings.qdrant_collection,
        settings.qdrant_vector_size,
    )
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=qmodels.VectorParams(
            size=settings.qdrant_vector_size,
            distance=qmodels.Distance.COSINE,
        ),
    )
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="notebook_id",
        field_schema=qmodels.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="source_id",
        field_schema=qmodels.PayloadSchemaType.KEYWORD,
    )


def delete_points_by_source(source_id: str, client: QdrantClient | None = None) -> None:
    """Removes all points for a source (via the `source_id` payload index) so
    deleting a source doesn't leave orphaned vectors behind (architecture doc
    §22.3 deletion concept).
    """
    settings = get_settings()
    client = client or get_qdrant_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="source_id", match=qmodels.MatchValue(value=source_id)
                    )
                ]
            )
        ),
        wait=True,
    )


if __name__ == "__main__":
    # `make qdrant-setup` entrypoint: python -m app.qdrant.client
    ensure_collection()
    print("Qdrant collection ready.")
