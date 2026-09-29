"""Redis/RQ queue helpers used by the API to enqueue worker jobs.

Two queue names are defined ("default" and "embeddings"). The API currently
enqueues everything on "default"; the worker listens on both.
"""

from functools import lru_cache

import redis
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import models

DEFAULT_QUEUE = "default"
EMBEDDINGS_QUEUE = "embeddings"


@lru_cache
def get_redis_connection() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url)


def get_queue(name: str = DEFAULT_QUEUE) -> Queue:
    return Queue(name, connection=get_redis_connection())


async def enqueue_process_source(db: AsyncSession, source_id: str, notebook_id: str) -> str:
    """Creates a `jobs` row (Postgres stays the source of truth for status,
    not Redis) and enqueues the worker job that parses,
    chunks, embeds and indexes the source.

    The worker package owns the job function implementation; the API only
    references its dotted path so the two services stay independently
    deployable (no shared Python import between api and worker).
    """
    job = models.Job(
        type="process_source", status="queued", source_id=source_id, notebook_id=notebook_id
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # NOTE: the kwarg must not be named `job_id` - RQ reserves that name for
    # the *queue* job's own id and would silently swallow it instead of
    # forwarding it to process_source().
    queue = get_queue(DEFAULT_QUEUE)
    queue.enqueue(
        "app.jobs.process_source.process_source",
        db_job_id=str(job.id),
        source_id=source_id,
        notebook_id=notebook_id,
        job_timeout="30m",
    )
    return str(job.id)
