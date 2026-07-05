"""SQLAlchemy models mirrored from apps/api/app/db/models.py.

The worker only needs a subset of columns to update job/source status and
insert chunks, but the table shapes must stay in sync with the API's models
and the Alembic migrations owned by the API service. Migrations are only
ever run from the api service (`make migrate`).

Deliberately no `ForeignKey(...)` declarations here: the worker's metadata
never includes `notebooks`/`users`, so SQLAlchemy couldn't resolve the
referenced tables, and it doesn't run DDL anyway. Referential integrity is
enforced by Postgres via the migrations the api service owns.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _uuid_col(nullable: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), nullable=nullable)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = _uuid_pk()
    notebook_id: Mapped[uuid.UUID] = _uuid_col()
    uploaded_by: Mapped[uuid.UUID] = _uuid_col()
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    notebook_id: Mapped[uuid.UUID] = _uuid_col()
    source_id: Mapped[uuid.UUID] = _uuid_col()
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(32), default="text", nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    source_id: Mapped[uuid.UUID | None] = _uuid_col(nullable=True)
    notebook_id: Mapped[uuid.UUID | None] = _uuid_col(nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LangdockRequest(Base):
    __tablename__ = "langdock_requests"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = _uuid_col(nullable=True)
    notebook_id: Mapped[uuid.UUID | None] = _uuid_col(nullable=True)
    job_id: Mapped[uuid.UUID | None] = _uuid_col(nullable=True)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
