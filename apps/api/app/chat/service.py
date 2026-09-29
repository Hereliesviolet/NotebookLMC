"""Chat / RAG orchestration (full sequence):

User Question -> [Haiku Intent Detection] -> [Haiku Query Rewrite]
              -> Langdock Query Embedding -> Qdrant Similarity Search
              -> Score Heuristic -> Context Assembly
              -> Sonnet Answer Generation -> Citation Validation
              -> Response mit Quellenkarten

Langdock-Aufrufe (Anthropic/OpenAI) laufen ueber den asyncen LangdockClient
(siehe langdock/client.py) und blockieren den Event-Loop damit nicht mehr.
Der Qdrant-Python-Client bleibt bewusst synchron (rag/retrieval.py, geteilte
Qdrant-Aufbau-Logik mit potenziellen zukuenftigen Sync-Konsumenten) - dessen
search_notebook()/backfill_missing_sources()-Aufrufe werden hier stattdessen
explizit in asyncio.to_thread() ausgelagert, damit sie den Event-Loop
ebenfalls nicht blockieren.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import models
from app.langdock.client import ResponseTruncatedError, get_langdock_client
from app.langdock.prompts_loader import load_final_answer_tool, load_prompt
from app.rag import query_understanding
from app.rag.citation_validation import downgrade_confidence_if_unsupported, validate_citations
from app.rag.context_assembly import build_context_block, fetch_chunk_texts
from app.rag.retrieval import (
    RetrievedChunk,
    apply_score_heuristic,
    backfill_missing_sources,
    search_notebook,
)
from app.schemas.chat import ChatRequest, ChatResponse

logger = get_logger(__name__)

# Notebook-Overview-artige Intents (siehe haiku_intent_detection.md): fuer diese
# Fragen wird der Diversitaets-Cap in apply_score_heuristic() auf 1 verschaerft,
# damit moeglichst jede Quelle im Notebook einen Slot bekommt statt nur die
# thematisch am naechsten liegende(n) Quelle(n).
OVERVIEW_INTENTS = {"summary", "briefing"}


async def answer_question(
    db: AsyncSession, notebook_id: str, user_id: str, payload: ChatRequest
) -> ChatResponse:
    settings = get_settings()
    client = get_langdock_client()

    db.add(
        models.Message(
            notebook_id=notebook_id, user_id=user_id, role="user", content=payload.message
        )
    )
    await db.commit()

    intent = None
    search_queries = [payload.message]
    if settings.enable_intent_detection:
        intent = await query_understanding.detect_intent(client, payload.message)
        logger.info("detected intent=%s for notebook=%s", intent, notebook_id)
    if settings.enable_query_rewrite:
        search_queries = await query_understanding.rewrite_query(client, payload.message)

    retrieved_by_id: dict[str, RetrievedChunk] = {}
    primary_embedding: list[float] | None = None
    try:
        # Ein gebatchter embed()-Aufruf statt einem Call pro Query - Langdock
        # gibt die Vektoren in derselben Reihenfolge wie die Eingabetexte
        # zurueck (OpenAI-Embeddings-API-Konvention), daher per zip() wieder
        # den einzelnen search_queries zuordenbar.
        embedding = await client.embed(search_queries)
        for query, vector in zip(search_queries, embedding.vectors):
            if primary_embedding is None:
                primary_embedding = vector
            chunks = await asyncio.to_thread(
                search_notebook, notebook_id, vector, source_ids=payload.source_ids
            )
            for chunk in chunks:
                existing = retrieved_by_id.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    retrieved_by_id[chunk.chunk_id] = chunk

        if primary_embedding is not None:
            backfilled = await asyncio.to_thread(
                backfill_missing_sources,
                notebook_id,
                primary_embedding,
                list(retrieved_by_id.values()),
                source_ids=payload.source_ids,
            )
            for chunk in backfilled:
                existing = retrieved_by_id.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    retrieved_by_id[chunk.chunk_id] = chunk
    except Exception as exc:
        logger.exception(
            "Retrieval (query embedding / Qdrant search) failed for notebook=%s", notebook_id
        )
        response = ChatResponse(
            answer="Die Suche in den Quellen ist derzeit nicht verfügbar. Bitte versuche es später erneut.",
            citations=[],
            confidence="low",
            missing_information=[f"Langdock/Qdrant-Fehler bei der Suche: {exc}"],
            follow_up_questions=[],
        )
        await _persist_assistant_message(db, notebook_id, user_id, response, model=None)
        return response

    max_chunks_per_source = 1 if intent in OVERVIEW_INTENTS else None
    top_chunks = apply_score_heuristic(
        list(retrieved_by_id.values()), max_chunks_per_source=max_chunks_per_source
    )

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
    final_answer_tool = load_final_answer_tool()
    user_message = f"Frage:\n{payload.message}\n\nQuellenkontext:\n{context}"

    answer_max_tokens = settings.chat_answer_max_tokens
    try:
        raw, usage = await client.tool_output(
            "sonnet",
            system_prompt,
            user_message,
            tool=final_answer_tool,
            max_tokens=answer_max_tokens,
        )
    except ResponseTruncatedError as exc:
        retry_max_tokens = answer_max_tokens * 2
        logger.warning(
            "Sonnet answer truncated (stop_reason=%s) for notebook=%s, retrying once with max_tokens=%s",
            exc.stop_reason,
            notebook_id,
            retry_max_tokens,
        )
        try:
            raw, usage = await client.tool_output(
                "sonnet",
                system_prompt,
                user_message,
                tool=final_answer_tool,
                max_tokens=retry_max_tokens,
            )
        except ResponseTruncatedError as retry_exc:
            logger.error(
                "Sonnet answer still truncated after retry (max_tokens=%s) for notebook=%s: %s",
                retry_max_tokens,
                notebook_id,
                retry_exc,
            )
            return await _persist_and_return(
                db,
                notebook_id,
                user_id,
                answer=(
                    "Die Antwort war zu lang und wurde abgeschnitten - bitte stelle eine "
                    "präzisere oder engere Frage."
                ),
                missing_information=[
                    f"Antwort auch nach Retry mit max_tokens={retry_max_tokens} abgeschnitten: {retry_exc}"
                ],
            )
        except Exception as retry_exc:
            logger.exception(
                "Sonnet answer generation failed on retry for notebook=%s", notebook_id
            )
            return await _persist_and_return(
                db,
                notebook_id,
                user_id,
                answer="Die Antwortgenerierung ist derzeit nicht verfügbar. Bitte versuche es später erneut.",
                missing_information=[f"Langdock-Fehler: {retry_exc}"],
            )
    except Exception as exc:
        logger.exception("Sonnet answer generation failed for notebook=%s", notebook_id)
        return await _persist_and_return(
            db,
            notebook_id,
            user_id,
            answer="Die Antwortgenerierung ist derzeit nicht verfügbar. Bitte versuche es später erneut.",
            missing_information=[f"Langdock-Fehler: {exc}"],
        )

    validated_citations = await validate_citations(db, notebook_id, raw.get("citations") or [])
    confidence = downgrade_confidence_if_unsupported(
        raw.get("confidence", "medium"), len(validated_citations)
    )

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


async def _persist_and_return(
    db: AsyncSession,
    notebook_id: str,
    user_id: str,
    answer: str,
    missing_information: list[str],
) -> ChatResponse:
    response = ChatResponse(
        answer=answer,
        citations=[],
        confidence="low",
        missing_information=missing_information,
        follow_up_questions=[],
    )
    await _persist_assistant_message(db, notebook_id, user_id, response, model=None)
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
    """Best-effort audit trail (langdock_requests table)."""
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
