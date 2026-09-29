from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import AuthenticatedUser, get_current_user, get_db
from app.jobs.queue import enqueue_process_source
from app.notebooks import service as notebooks_service
from app.schemas.source import SourceOut, SourceUploadResponse
from app.sources import service
from app.sources.upload import UnsupportedFileTypeError, resolve_mime_type

router = APIRouter(prefix="/api", tags=["sources"])


def _to_out(source) -> SourceOut:
    return SourceOut(
        id=str(source.id),
        notebook_id=str(source.notebook_id),
        filename=source.filename,
        original_filename=source.original_filename,
        mime_type=source.mime_type,
        status=source.status,
        page_count=source.page_count,
        token_count=source.token_count,
        error_message=source.error_message,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.get("/notebooks/{notebook_id}/sources", response_model=list[SourceOut])
async def list_sources(
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[SourceOut]:
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)
    sources = await service.list_sources(db, notebook_id)
    return [_to_out(s) for s in sources]


@router.post(
    "/notebooks/{notebook_id}/sources/upload", response_model=SourceUploadResponse, status_code=201
)
async def upload_source(
    notebook_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SourceUploadResponse:
    """Upload pipeline step 1-5:
    validate -> store in MinIO -> create `sources` row -> enqueue worker job.
    """
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)

    settings = get_settings()
    data = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb}MB upload limit",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )

    try:
        mime_type = resolve_mime_type(file.filename or "upload", file.content_type)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc

    source = await service.create_source(
        db,
        notebook_id=notebook_id,
        uploaded_by=user.id,
        original_filename=file.filename or "upload",
        mime_type=mime_type,
        data=data,
    )
    job_id = await enqueue_process_source(db, source_id=str(source.id), notebook_id=notebook_id)

    return SourceUploadResponse(source=_to_out(source), job_id=job_id)


@router.post("/sources/{source_id}/reprocess", response_model=SourceUploadResponse)
async def reprocess_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SourceUploadResponse:
    source = await service.get_source_or_404(db, source_id)
    notebook = await notebooks_service.get_notebook_or_404(db, str(source.notebook_id))
    notebooks_service.assert_can_access(notebook, user.id)

    source.status = "uploaded"
    source.error_message = None
    await db.commit()
    await db.refresh(source)

    job_id = await enqueue_process_source(
        db, source_id=str(source.id), notebook_id=str(source.notebook_id)
    )
    return SourceUploadResponse(source=_to_out(source), job_id=job_id)


@router.get("/sources/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SourceOut:
    source = await service.get_source_or_404(db, source_id)
    notebook = await notebooks_service.get_notebook_or_404(db, str(source.notebook_id))
    notebooks_service.assert_can_access(notebook, user.id)
    return _to_out(source)


@router.delete("/sources/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    source = await service.get_source_or_404(db, source_id)
    notebook = await notebooks_service.get_notebook_or_404(db, str(source.notebook_id))
    notebooks_service.assert_can_access(notebook, user.id)
    await service.delete_source_and_artifacts(db, source)
