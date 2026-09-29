"""RQ worker entrypoint.

Listens on two queues:
  - "embeddings": Langdock embedding calls, kept separate so its
    concurrency can be tuned independently (WORKER_EMBEDDING_CONCURRENCY).
  - "default": parsing, chunking, Qdrant indexing, status updates.

Run one worker process per queue in production if you need different
concurrency; for local dev a single process handling both is enough.
"""

import redis
from rq import Worker

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.jobs.process_source import process_source  # noqa: F401  registers the job function

QUEUES = ["embeddings", "default"]


def main() -> None:
    settings = get_settings()
    configure_logging(settings.app_env)
    logger = get_logger(__name__)
    logger.info("starting worker, listening on queues: %s", QUEUES)

    connection = redis.from_url(settings.redis_url)
    worker = Worker(QUEUES, connection=connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
