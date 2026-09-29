"""RQ worker entrypoint.

Listens on two queues, "embeddings" and "default". The API only enqueues
`process_source` on "default" today, which runs parsing, chunking,
embedding and indexing in one job. The second queue is there so embedding
work can be split off later; a single process handles both.
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
