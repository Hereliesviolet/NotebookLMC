"""Studio endpoints (architecture doc §19, §26.5).

summary/faq/timeline/briefing are fully implemented (MVP2). audio-script
stays a 501 placeholder, planned for later.
"""
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthenticatedUser, get_current_user, get_db
from app.core.logging import get_logger
from app.db import models
from app.notebooks import service as notebooks_service
from app.schemas.studio import StudioArtifactOut
from app.studio import export as export_service
from app.studio import service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notebooks", tags=["studio"])

_EXPORT_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


def _not_implemented(name: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Studio feature '{name}' is planned for MVP2, see docs/architecture.md §19",
    )


def _to_out(artifact: models.StudioArtifact) -> StudioArtifactOut:
    return StudioArtifactOut(
        id=str(artifact.id),
        notebook_id=str(artifact.notebook_id),
        type=artifact.type,
        content=artifact.content_json,
        source_ids=artifact.source_ids_json or [],
        model=artifact.model,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


async def _get_notebook_checked(db: AsyncSession, notebook_id: str, user: AuthenticatedUser) -> None:
    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)


async def _generate(notebook_id: str, artifact_type: str, db: AsyncSession, user: AuthenticatedUser) -> StudioArtifactOut:
    await _get_notebook_checked(db, notebook_id, user)
    try:
        artifact = await service.generate_artifact(db, notebook_id, artifact_type)
    except service.NoIndexedSourcesError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except service.StudioGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return _to_out(artifact)


@router.get("/{notebook_id}/studio/{artifact_type}", response_model=StudioArtifactOut)
async def get_studio_artifact(
    notebook_id: str,
    artifact_type: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> StudioArtifactOut:
    if artifact_type not in service.STUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown studio artifact type: '{artifact_type}'"
        )
    await _get_notebook_checked(db, notebook_id, user)
    artifact = await service.get_artifact(db, notebook_id, artifact_type)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No '{artifact_type}' artifact has been generated yet for this notebook",
        )
    return _to_out(artifact)


@router.get("/{notebook_id}/studio/{artifact_type}/export")
async def export_studio_artifact(
    notebook_id: str,
    artifact_type: str,
    format: str = "docx",
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    if artifact_type not in service.STUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown studio artifact type: '{artifact_type}'"
        )
    if format not in _EXPORT_MEDIA_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be 'docx' or 'pdf'")

    notebook = await notebooks_service.get_notebook_or_404(db, notebook_id)
    notebooks_service.assert_can_access(notebook, user.id)

    artifact = await service.get_artifact(db, notebook_id, artifact_type)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No '{artifact_type}' artifact has been generated yet for this notebook",
        )

    try:
        if format == "docx":
            document = export_service.build_docx(artifact_type, notebook.title, artifact.content_json, artifact.updated_at)
            file_bytes = export_service.render_docx_bytes(document)
        else:
            html_content = export_service.build_html(
                artifact_type, notebook.title, artifact.content_json, artifact.updated_at
            )
            file_bytes = export_service.render_pdf_bytes(html_content)
    except Exception as exc:
        logger.exception("Studio export failed for notebook=%s type=%s format=%s", notebook_id, artifact_type, format)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export fehlgeschlagen: {exc}"
        ) from exc

    filename_ascii = export_service.safe_filename(f"{notebook.title}-{artifact_type}", format)
    filename_utf8 = quote(f"{notebook.title}-{artifact_type}.{format}")
    headers = {"Content-Disposition": f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{filename_utf8}"}
    return StreamingResponse(BytesIO(file_bytes), media_type=_EXPORT_MEDIA_TYPES[format], headers=headers)


@router.post("/{notebook_id}/studio/summary", response_model=StudioArtifactOut)
async def studio_summary(
    notebook_id: str, db: AsyncSession = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)
) -> StudioArtifactOut:
    return await _generate(notebook_id, "summary", db, user)


@router.post("/{notebook_id}/studio/faq", response_model=StudioArtifactOut)
async def studio_faq(
    notebook_id: str, db: AsyncSession = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)
) -> StudioArtifactOut:
    return await _generate(notebook_id, "faq", db, user)


@router.post("/{notebook_id}/studio/timeline", response_model=StudioArtifactOut)
async def studio_timeline(
    notebook_id: str, db: AsyncSession = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)
) -> StudioArtifactOut:
    return await _generate(notebook_id, "timeline", db, user)


@router.post("/{notebook_id}/studio/briefing", response_model=StudioArtifactOut)
async def studio_briefing(
    notebook_id: str, db: AsyncSession = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)
) -> StudioArtifactOut:
    return await _generate(notebook_id, "briefing", db, user)


@router.post("/{notebook_id}/studio/audio-script")
async def studio_audio_script(notebook_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    _not_implemented("audio-script")
