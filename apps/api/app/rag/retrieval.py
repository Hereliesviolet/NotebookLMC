"""Qdrant retrieval step of the RAG pipeline.

Dense vector search scoped to the current notebook (+ optional source
filter), with a simple MVP score/order heuristic instead of full LLM
reranking (Haiku reranking is a possible future upgrade, disabled
by RERANKER_ENABLED=false by default).
"""

from dataclasses import dataclass

from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import get_logger
from app.qdrant.client import get_qdrant_client

logger = get_logger(__name__)

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
    notebook_id: str,
    query_vector: list[float],
    source_ids: list[str] | None = None,
    limit: int = RETRIEVAL_TOP_K,
) -> list[RetrievedChunk]:
    settings = get_settings()
    client = get_qdrant_client()

    must_conditions = [
        qmodels.FieldCondition(key="notebook_id", match=qmodels.MatchValue(value=notebook_id))
    ]
    if source_ids:
        must_conditions.append(
            qmodels.FieldCondition(key="source_id", match=qmodels.MatchAny(any=source_ids))
        )

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


def list_notebook_source_ids(notebook_id: str, source_ids: list[str] | None = None) -> set[str]:
    """Cheap Qdrant scroll (id-order, no vector similarity/embedding call) to
    discover every source_id that actually exists in a notebook - used by
    backfill_missing_sources() to detect sources missing from the similarity
    candidate pool entirely (see its docstring for why that matters).
    """
    settings = get_settings()
    client = get_qdrant_client()
    must_conditions = [
        qmodels.FieldCondition(key="notebook_id", match=qmodels.MatchValue(value=notebook_id))
    ]
    if source_ids:
        must_conditions.append(
            qmodels.FieldCondition(key="source_id", match=qmodels.MatchAny(any=source_ids))
        )
    scroll_filter = qmodels.Filter(must=must_conditions)

    found: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=scroll_filter,
            with_payload=["source_id"],
            with_vectors=False,
            limit=256,
            offset=offset,
        )
        found.update(p.payload.get("source_id") for p in points if p.payload.get("source_id"))
        if offset is None:
            break
    return found


def backfill_missing_sources(
    notebook_id: str,
    query_vector: list[float],
    existing_chunks: list[RetrievedChunk],
    source_ids: list[str] | None = None,
    per_source_limit: int = 2,
) -> list[RetrievedChunk]:
    """Guarantees every source in the notebook has at least one candidate to
    diversify over in apply_score_heuristic().

    A single dominant source (e.g. 106 chunks vs. 2-3 for the rest) can occupy
    the *entire* RETRIEVAL_TOP_K similarity ranking on a broad/generic
    question - verified live: minor sources only appeared around rank 34-102
    of the full per-notebook ranking, far outside RETRIEVAL_TOP_K=30. No
    amount of re-ranking within an empty candidate set fixes that, so unlike
    apply_score_heuristic() this does issue one small, local, non-Langdock
    Qdrant search per source still missing after the main search - cheap
    compared to the per-source-per-query-rewrite alternative of always
    searching every source individually.
    """
    covered = {c.source_id for c in existing_chunks}
    missing = list_notebook_source_ids(notebook_id, source_ids=source_ids) - covered
    if not missing:
        return []

    backfilled: list[RetrievedChunk] = []
    for source_id in missing:
        backfilled.extend(
            search_notebook(
                notebook_id, query_vector, source_ids=[source_id], limit=per_source_limit
            )
        )
    return backfilled


def apply_score_heuristic(
    chunks: list[RetrievedChunk],
    top_k: int = CONTEXT_TOP_K,
    max_chunks_per_source: int | None = None,
) -> list[RetrievedChunk]:
    """MVP heuristic with a per-source diversity guarantee.

    Plain global top-k by score lets one large/generic source occupy every
    slot on broad questions, silently excluding a notebook's other sources
    from the answer even though Qdrant retrieved them correctly. Fix:
    round-robin the per-source score-sorted lists (capped at
    max_chunks_per_source) so every source gets its best chunk(s) first, then
    fill any remaining slots with the overall next-best chunks regardless of
    source so relevance still decides the rest of the budget. Operates only
    on the already-fetched RETRIEVAL_TOP_K candidate list - no extra Qdrant
    call per source.
    """
    if max_chunks_per_source is None:
        max_chunks_per_source = get_settings().context_max_chunks_per_source

    by_source: dict[str, list[RetrievedChunk]] = {}
    for chunk in chunks:
        by_source.setdefault(chunk.source_id, []).append(chunk)
    for source_chunks in by_source.values():
        source_chunks.sort(key=lambda c: c.score, reverse=True)

    selected: list[RetrievedChunk] = []
    selected_ids: set[str] = set()

    round_index = 0
    while len(selected) < top_k and round_index < max_chunks_per_source:
        progressed = False
        for source_chunks in by_source.values():
            if round_index >= len(source_chunks):
                continue
            chunk = source_chunks[round_index]
            selected.append(chunk)
            selected_ids.add(chunk.chunk_id)
            progressed = True
            if len(selected) >= top_k:
                break
        if not progressed:
            break
        round_index += 1

    if len(selected) < top_k:
        remaining = sorted(
            (c for c in chunks if c.chunk_id not in selected_ids),
            key=lambda c: c.score,
            reverse=True,
        )
        selected.extend(remaining[: top_k - len(selected)])

    return sorted(selected, key=lambda c: c.score, reverse=True)
