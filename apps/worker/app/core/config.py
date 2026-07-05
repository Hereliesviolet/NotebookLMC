"""Worker settings.

Deliberately duplicated from apps/api/app/core/config.py rather than shared
via an importable package (see implementation plan §7 "Empfehlung
Code-Sharing"): api and worker stay independently deployable, and the
settings surface here is a subset of what the API needs.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # Langdock
    langdock_api_key: str = ""
    langdock_region: str = "eu"
    langdock_anthropic_base_url: str = "https://api.langdock.com/anthropic/eu/v1"
    langdock_primary_model: str = ""
    langdock_fast_model: str = ""
    langdock_enable_extended_thinking: bool = False

    # Embeddings (Langdock OpenAI-compatible endpoint)
    embedding_provider: str = "langdock"
    embedding_base_url: str = "https://api.langdock.com/openai/eu/v1"
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536
    embedding_encoding_format: str = "float"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "notebook"
    postgres_user: str = "notebook"
    postgres_password: str = "notebook"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "notebook_chunks"
    qdrant_vector_size: int = 1536

    # MinIO
    minio_endpoint: str = "http://minio:9000"
    minio_bucket: str = "notebook-files"
    minio_root_user: str = "minio"
    minio_root_password: str = "minio-password"
    minio_use_ssl: bool = False

    # Worker / queue tuning
    worker_embedding_concurrency: int = 2
    worker_default_concurrency: int = 2
    langdock_retry_backoff_seconds: str = "5,15,30,60"

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def retry_backoff_seconds(self) -> list[int]:
        return [int(x) for x in self.langdock_retry_backoff_seconds.split(",") if x]


@lru_cache
def get_settings() -> Settings:
    return Settings()
