"""MinIO client wrapper - mirrored from apps/api/app/storage/minio_client.py."""
import io
from functools import lru_cache
from urllib.parse import urlparse

from minio import Minio

from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    parsed = urlparse(settings.minio_endpoint)
    return Minio(
        endpoint=parsed.netloc or parsed.path,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
    )


def original_object_path(notebook_id: str, source_id: str, filename: str) -> str:
    return f"{notebook_id}/{source_id}/original/{filename}"


def extracted_text_path(notebook_id: str, source_id: str) -> str:
    return f"{notebook_id}/{source_id}/extracted/text.txt"


def download_bytes(object_path: str) -> bytes:
    settings = get_settings()
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, object_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(object_path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    settings = get_settings()
    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        object_path,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def delete_object(object_path: str) -> None:
    settings = get_settings()
    client = get_minio_client()
    client.remove_object(settings.minio_bucket, object_path)
