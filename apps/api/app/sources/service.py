import asyncio
import hashlib
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.qdrant.client import delete_points_by_source
from app.storage.minio_client import delete_object, original_object_path, upload_bytes


async def create_source(
    db: AsyncSession,
    notebook_id: str,
    uploaded_by: str,
    original_filename: str,
    mime_type: str,
    data: bytes,
) -> models.Source:
    checksum = hashlib.sha256(data).hexdigest()
    source = models.Source(
        notebook_id=notebook_id,
        uploaded_by=uploaded_by,
        filename=original_filename,
        original_filename=original_filename,
        mime_type=mime_type,
        storage_path="",  # filled in once we know the generated source id
        status="uploaded",
        checksum=checksum,
    )
    db.add(source)
    await db.flush()  # assigns source.id without committing yet

    storage_path = original_object_path(notebook_id, str(source.id), original_filename)
    upload_bytes(storage_path, data, content_type=mime_type)

    source.storage_path = storage_path
    await db.commit()
    await db.refresh(source)
    return source


async def delete_source_and_artifacts(db: AsyncSession, source: models.Source) -> None:
    """Removes DB row, chunks (cascade via FK), the MinIO object and the
    Qdrant points (§22.3 deletion concept). Jobs referencing this source
    cascade-delete at the DB level too (jobs_source_id_fkey ON DELETE CASCADE).
    """
    if source.storage_path:
        try:
            delete_object(source.storage_path)
        except Exception:
            pass  # best-effort; DB row deletion must not be blocked by storage errors
    try:
        # Qdrant-Client ist synchron (siehe qdrant/client.py) - in einem
        # Thread ausgefuehrt, damit dieser async-Endpunkt (sources/router.py
        # delete_source) den Event-Loop dafuer nicht blockiert.
        await asyncio.to_thread(delete_points_by_source, str(source.id))
    except Exception:
        pass  # best-effort; DB row deletion must not be blocked by Qdrant errors
    await db.delete(source)
    await db.commit()


async def list_sources(db: AsyncSession, notebook_id: str) -> list[models.Source]:
    result = await db.execute(
        select(models.Source)
        .where(models.Source.notebook_id == notebook_id)
        .order_by(models.Source.created_at.desc())
    )
    return list(result.scalars().all())


async def get_source_or_404(db: AsyncSession, source_id: str) -> models.Source:
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    source = await db.get(models.Source, source_uuid)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source
