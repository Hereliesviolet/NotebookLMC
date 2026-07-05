"""Qdrant retrieval step of the RAG pipeline (architecture doc §16.3).

Dense vector search scoped to the current notebook (+ optional source
filter), with a simple MVP score/order heuristic instead of full LLM
reranking (§7.4 - Haiku reranking is a documented future upgrade, disabled
by RERANKER_ENABLED=false by default).
"""
from dataclasses import dataclass

from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.qdrant.client import get_qdrant_client

RETRIEVAL_TOP_K = 30
CONTEXT_TOP_K = 10


@dataclass
class RetrievedChunk:
    chunk_id: str
    score: float
    source_id: str
    document_name: str
    page_start: int | None
    page_end: int | None
    heading: str | None
    chunk_type: str


def search_notebook(
    notebook_id: str, query_vector: list[float], source_ids: list[str] | None = None, limit: int = RETRIEVAL_TOP_K
) -> list[RetrievedChunk]:
    settings = get_settings()
    client = get_qdrant_client()

    must_conditions = [qmodels.FieldCondition(key="notebook_id", match=qmodels.MatchValue(value=notebook_id))]
    if source_ids:
        must_conditions.append(qmodels.FieldCondition(key="source_id", match=qmodels.MatchAny(any=source_ids)))

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=qmodels.Filter(must=must_conditions),
        limit=limit,
        with_payload=True,
    )

    return [
        RetrievedChunk(
            chunk_id=str(point.id),
            score=point.score,
            source_id=point.payload.get("source_id", ""),
            document_name=point.payload.get("document_name", ""),
            page_start=point.payload.get("page_start"),
            page_end=point.payload.get("page_end"),
            heading=point.payload.get("heading"),
            chunk_type=point.payload.get("chunk_type", "text"),
        )
        for point in results
    ]


def apply_score_heuristic(chunks: list[RetrievedChunk], top_k: int = CONTEXT_TOP_K) -> list[RetrievedChunk]:
    """MVP heuristic (architecture doc §7.4): Qdrant already returns results
    sorted by cosine score descending, so this just truncates to top_k.
    Kept as its own function so a real heuristic (e.g. per-document dedup,
    minimum score threshold) or Haiku reranking can slot in later without
    touching call sites.
    """
    return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]
