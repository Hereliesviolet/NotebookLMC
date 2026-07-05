"""Central application settings, loaded from environment variables (.env).

All values that could differ between dev/staging/production - including
Langdock model ids - are read exclusively from the environment. Nothing
here hardcodes a real Langdock model id or API key.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    # Langdock
    langdock_api_key: str = ""
    langdock_region: str = "eu"
    langdock_anthropic_base_url: str = "https://api.langdock.com/anthropic/eu/v1"
    langdock_primary_model: str = ""
    langdock_fast_model: str = ""
    langdock_enable_extended_thinking: bool = False
    langdock_agent_base_url: str = "https://api.langdock.com/agent/v1"
    langdock_use_agents_for_structured_tasks: bool = False
    langdock_knowledge_api_enabled: bool = False
    langdock_knowledge_base_url: str = "https://api.langdock.com/knowledge"
    langdock_usage_export_enabled: bool = False

    # Embeddings (Langdock OpenAI-compatible endpoint)
    embedding_provider: str = "langdock"
    embedding_base_url: str = "https://api.langdock.com/openai/eu/v1"
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536
    embedding_encoding_format: str = "float"

    # Reranking
    reranker_provider: str = "langdock_haiku"
    reranker_model: str = ""
    reranker_enabled: bool = False

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

    # Dev / demo auth
    dev_auth_enabled: bool = True
    dev_demo_user_email: str = "demo@notebooklm.local"
    dev_demo_user_name: str = "Demo User"

    # Upload limits (architecture doc §22.1)
    max_upload_size_mb: int = 50

    # RAG pipeline (architecture doc §16.1) - intent detection and query
    # rewrite are prepared but optional for the MVP core flow per the
    # implementation plan; the core retrieval->answer->citation flow always
    # runs regardless of these flags.
    enable_intent_detection: bool = False
    enable_query_rewrite: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Used by Alembic, which runs migrations synchronously."""
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
