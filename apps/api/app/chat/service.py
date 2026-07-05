"""Chat / RAG orchestration (architecture doc §16.1, full sequence):

User Question -> [Haiku Intent Detection] -> [Haiku Query Rewrite]
              -> Langdock Query Embedding -> Qdrant Similarity Search
              -> Score Heuristic -> Context Assembly
              -> Sonnet 5 Answer Generation -> Citation Validation
              -> Response mit Quellenkarten
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import models
from app.langdock.client import get_langdock_client
from app.langdock.prompts_loader import load_output_schema, load_prompt
from app.rag import query_understanding
from app.rag.citation_validation import downgrade_confidence_if_unsupported, validate_citations
from app.rag.context_assembly import build_context_block, fetch_chunk_texts
from app.rag.retrieval import RetrievedChunk, apply_score_heuristic, search_notebook
from app.schemas.chat import ChatRequest, ChatResponse

logger = get_logger(__name__)


async def answer_question(
    db: AsyncSession, notebook_id: str, user_id: str, payload: ChatRequest
) -> ChatResponse:
    settings = get_settings()
    client = get_langdock_client()

    db.add(models.Message(notebook_id=notebook_id, user_id=user_id, role="user", content=payload.message))
    await db.commit()

    search_queries = [payload.message]
    if settings.enable_intent_detection:
        intent = query_understanding.detect_intent(client, payload.message)
        logger.info("detected intent=%s for notebook=%s", intent, notebook_id)
    if settings.enable_query_rewrite:
        search_queries = query_understanding.rewrite_query(client, payload.message)

    retrieved_by_id: dict[str, RetrievedChunk] = {}
    try:
        for query in search_queries:
            embedding = client.embed([query])
            if not embedding.vectors:
                continue
            for chunk in search_notebook(notebook_id, embedding.vectors[0], source_ids=payload.source_ids):
                existing = retrieved_by_id.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    retrieved_by_id[chunk.chunk_id] = chunk
    except Exception as exc:
        logger.exception("Retrieval (query embedding / Qdrant search) failed for notebook=%s", notebook_id)
        response = ChatResponse(
            answer="Die Suche in den Quellen ist derzeit nicht verfügbar. Bitte versuche es später erneut.",
            citations=[],
            confidence="low",
            missing_information=[f"Langdock/Qdrant-Fehler bei der Suche: {exc}"],
            follow_up_questions=[],
        )
        await _persist_assistant_message(db, notebook_id, user_id, response, model=None)
        return response

    top_chunks = apply_score_heuristic(list(retrieved_by_id.values()))

    if not top_chunks:
        response = ChatResponse(
            answer="Ich konnte in den hochgeladenen Quellen keine relevanten Informationen zu dieser Frage finden.",
            citations=[],
            confidence="low",
            missing_information=["Keine passenden Chunks in den indexierten Quellen gefunden."],
            follow_up_questions=[],
        )
        await _persist_assistant_message(db, notebook_id, user_id, response, model=None)
        return response

    texts_by_chunk_id = await fetch_chunk_texts(db, [c.chunk_id for c in top_chunks])
    context = build_context_block(top_chunks, texts_by_chunk_id)

    system_prompt = load_prompt("system_final_answer")
    schema = load_output_schema()
    user_message = (
        f"Output-Schema (JSON, exakt einhalten):\n{schema}\n\n"
        f"Frage:\n{payload.message}\n\n"
        f"Quellenkontext:\n{context}"
    )

    try:
        raw, usage = client.structured_output("sonnet", system_prompt, user_message, max_tokens=2048)
    except Exception as exc:
        logger.exception("Sonnet answer generation failed for notebook=%s", notebook_id)
        response = ChatResponse(
            answer="Die Antwortgenerierung ist derzeit nicht verfügbar. Bitte versuche es später erneut.",
            citations=[],
            confidence="low",
            missing_information=[f"Langdock-Fehler: {exc}"],
            follow_up_questions=[],
        )
        await _persist_assistant_message(db, notebook_id, user_id, response, model=None)
        return response

    validated_citations = await validate_citations(db, notebook_id, raw.get("citations") or [])
    confidence = downgrade_confidence_if_unsupported(raw.get("confidence", "medium"), len(validated_citations))

    response = ChatResponse(
        answer=raw.get("answer", ""),
        citations=validated_citations,
        confidence=confidence,
        missing_information=raw.get("missing_information") or [],
        follow_up_questions=raw.get("follow_up_questions") or [],
    )
    await _persist_assistant_message(db, notebook_id, user_id, response, model=usage.model)
    await _log_langdock_request(db, notebook_id, user_id, usage)
    return response


async def _persist_assistant_message(
    db: AsyncSession, notebook_id: str, user_id: str, response: ChatResponse, model: str | None
) -> None:
    message = models.Message(
        notebook_id=notebook_id,
        user_id=user_id,
        role="assistant",
        content=response.answer,
        model=model,
        citations_json=[c.model_dump() for c in response.citations],
    )
    db.add(message)
    await db.commit()


async def _log_langdock_request(db: AsyncSession, notebook_id: str, user_id: str, usage) -> None:
    """Best-effort audit trail (architecture doc §13.10 langdock_requests)."""
    try:
        db.add(
            models.LangdockRequest(
                user_id=user_id,
                notebook_id=notebook_id,
                request_type="completion",
                model=usage.model,
                status_code=usage.status_code,
                latency_ms=usage.latency_ms,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                error_message=usage.error_message,
            )
        )
        await db.commit()
    except Exception:
        logger.exception("failed to persist langdock_requests audit row (non-fatal)")
