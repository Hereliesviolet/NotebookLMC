"""Batch embedding calls via Langdock (OpenAI-compatible endpoint, ada-002).

Chunks -> LangdockClient.embed() -> vectors (architecture doc §7.3 / §13
embedding flow). Requests are batched to keep individual calls small and
retry-friendly (429 handling lives in LangdockClient itself, §23).
"""

from app.core.logging import get_logger
from app.langdock.client import get_langdock_client

logger = get_logger(__name__)

_BATCH_SIZE = 16


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = get_langdock_client()
    vectors: list[list[float]] = []

    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.embed(batch)
        vectors.extend(response.vectors)
        logger.info(
            "embedded batch of %d chunks (model=%s, latency_ms=%s)",
            len(batch),
            response.usage.model,
            response.usage.latency_ms,
        )

    return vectors
