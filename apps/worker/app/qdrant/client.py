"""Qdrant client wrapper - mirrored from apps/api/app/qdrant/client.py.

Collection design: collection notebook_chunks, vector size 1536, cosine
distance. The api service creates the collection
on startup; `ensure_collection` is called here too as a safety net in case
the worker's first indexing job runs before the api container is ready.
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
            size=settings.qdrant_vector_size, distance=qmodels.Distance.COSINE
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
    reprocessing a source doesn't leave points from a previous run behind
    (mirrored from apps/api/app/qdrant/client.py).
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
