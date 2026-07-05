from minio import Minio
from qdrant_client import QdrantClient
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.jobs.queue import get_redis_connection
from app.qdrant.client import get_qdrant_client
from app.storage.minio_client import get_minio_client

__all__ = [
    "AuthenticatedUser",
    "get_current_user",
    "get_db",
    "get_qdrant",
    "get_minio",
    "get_redis",
]


def get_qdrant() -> QdrantClient:
    return get_qdrant_client()


def get_minio() -> Minio:
    return get_minio_client()


def get_redis() -> Redis:
    return get_redis_connection()


AsyncSessionDep = AsyncSession
