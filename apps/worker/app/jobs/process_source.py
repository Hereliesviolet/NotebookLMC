"""Main document processing job (pipeline):

Upload -> MinIO (already done by the API) -> [this job] -> parse -> chunk
-> Langdock embeddings -> Qdrant upsert -> source.status = indexed

RQ calls this function by its dotted path (see apps/api/app/jobs/queue.py).
Each step below is implemented in its own module; this function only owns
orchestration, status transitions and error handling.
"""

import uuid

from sqlalchemy.orm import Session

from app.chunking.chunker import chunk_sections
from app.core.logging import get_logger
from app.db import models
from app.db.session import session_scope
from app.embeddings.langdock_embeddings import embed_texts
from app.indexing.qdrant_indexer import index_chunks
from app.jobs.status import (
    get_job,
    get_source,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    mark_source_no_content,
    set_source_status,
)
from app.parsing.registry import parse_document
from app.qdrant.client import delete_points_by_source
from app.storage.minio_client import download_bytes

logger = get_logger(__name__)


def _delete_existing_chunks(db: Session, source_id: str) -> None:
    """Removes chunk rows from a previous run before inserting the fresh set,
    so reprocessing a source never accumulates duplicate/stale chunks
    (regardless of whether that previous run succeeded or failed midway).
    """
    db.query(models.Chunk).filter(models.Chunk.source_id == uuid.UUID(source_id)).delete()


def process_source(db_job_id: str, source_id: str, notebook_id: str) -> None:
    job_id = db_job_id
    with session_scope() as db:
        job = get_job(db, job_id)
        source = get_source(db, source_id)
        mark_job_running(db, job)
        set_source_status(db, source, "processing")

    try:
        has_content = _run_pipeline(source_id=source_id, notebook_id=notebook_id)
        with session_scope() as db:
            job = get_job(db, job_id)
            source = get_source(db, source_id)
            mark_job_completed(db, job)
            if has_content:
                set_source_status(db, source, "indexed")
            else:
                mark_source_no_content(db, source)
        logger.info("source %s processed (has_content=%s)", source_id, has_content)
    except Exception as exc:  # noqa: BLE001 - we want to persist any failure
        logger.exception("processing source %s failed", source_id)
        with session_scope() as db:
            job = get_job(db, job_id)
            source = get_source(db, source_id)
            mark_job_failed(db, job, str(exc))
            set_source_status(db, source, "failed", error_message=str(exc))
        raise


def _run_pipeline(source_id: str, notebook_id: str) -> bool:
    """Returns whether the source produced indexable content (chunks/points).
    `False` means parsing (incl. OCR fallback) ran without error but yielded
    nothing - the caller marks the source `"no_content"` instead of `"indexed"`.
    """
    with session_scope() as db:
        source = get_source(db, source_id)
        storage_path = source.storage_path
        mime_type = source.mime_type
        original_filename = source.original_filename

    raw_bytes = download_bytes(storage_path)
    sections = parse_document(mime_type=mime_type, filename=original_filename, data=raw_bytes)
    chunk_drafts = chunk_sections(sections)

    if not chunk_drafts:
        logger.warning("no chunks produced for source %s", source_id)
        with session_scope() as db:
            source = get_source(db, source_id)
            _delete_existing_chunks(db, source_id)
            delete_points_by_source(source_id)
            source.page_count = None
            source.token_count = 0
        return False

    vectors = embed_texts([c.text for c in chunk_drafts])

    with session_scope() as db:
        source = get_source(db, source_id)

        _delete_existing_chunks(db, source_id)

        db_chunks = []
        for idx, draft in enumerate(chunk_drafts):
            chunk = models.Chunk(
                notebook_id=uuid.UUID(notebook_id),
                source_id=uuid.UUID(source_id),
                chunk_index=idx,
                chunk_type=draft.chunk_type,
                page_start=draft.page_start,
                page_end=draft.page_end,
                heading=draft.heading,
                text=draft.text,
                metadata_json=draft.metadata,
            )
            db.add(chunk)
            db_chunks.append(chunk)
        db.flush()  # assigns chunk.id (client-side uuid4 default) without committing yet

        # Remove any points left over from a previous run (e.g. different chunk
        # count/ids) before upserting the fresh set, so reprocessing never
        # leaves orphaned vectors in Qdrant.
        delete_points_by_source(source_id)
        point_ids = index_chunks(
            notebook_id=notebook_id,
            source_id=source_id,
            document_name=original_filename,
            chunks=db_chunks,
            vectors=vectors,
        )
        for chunk, point_id in zip(db_chunks, point_ids):
            chunk.qdrant_point_id = point_id
        source.page_count = _max_page(chunk_drafts)
        source.token_count = sum(len(c.text.split()) for c in chunk_drafts)

    return True


def _max_page(chunk_drafts: list) -> int | None:
    pages = [c.page_end for c in chunk_drafts if c.page_end is not None]
    return max(pages) if pages else None
