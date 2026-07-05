"""Job/source status helpers, shared by process_source and future job types."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models


def get_job(db: Session, job_id: str) -> models.Job:
    job = db.get(models.Job, uuid.UUID(job_id))
    if job is None:
        raise ValueError(f"Job {job_id} not found - it must be created by the API before enqueueing")
    return job


def get_source(db: Session, source_id: str) -> models.Source:
    source = db.get(models.Source, uuid.UUID(source_id))
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    return source


def mark_job_running(db: Session, job: models.Job) -> None:
    job.status = "running"
    job.error_message = None
    job.started_at = datetime.now(timezone.utc)
    db.commit()


def mark_job_completed(db: Session, job: models.Job) -> None:
    job.status = "completed"
    job.error_message = None
    job.completed_at = datetime.now(timezone.utc)
    db.commit()


def mark_job_failed(db: Session, job: models.Job, error_message: str) -> None:
    job.status = "failed"
    job.error_message = error_message[:4000]
    job.completed_at = datetime.now(timezone.utc)
    db.commit()


def set_source_status(db: Session, source: models.Source, status: str, error_message: str | None = None) -> None:
    """`error_message` always overwrites (including clearing to None on
    success) so a source that fails once and later succeeds on retry
    doesn't keep showing a stale error.
    """
    source.status = status
    source.error_message = error_message[:4000] if error_message else None
    db.commit()


NO_CONTENT_MESSAGE = (
    "Kein Text erkannt (auch nach OCR-Versuch) - Dokument enthält evtl. keine lesbaren Inhalte."
)


def mark_source_no_content(db: Session, source: models.Source) -> None:
    """Distinct from `"failed"`: parsing/OCR ran without error, but produced
    zero usable chunks (e.g. a blank/unreadable page) - so callers/the UI can
    tell "processing crashed" apart from "nothing to index in this file".
    """
    set_source_status(db, source, "no_content", error_message=NO_CONTENT_MESSAGE)
