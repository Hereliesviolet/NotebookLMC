"""Structured logging - mirrored from apps/api/app/core/logging.py.

Never log full document content, full prompts
with confidential source text, API keys or personal data.
"""

import logging
import sys

_CONFIGURED = False


def configure_logging(app_env: str = "development") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = logging.DEBUG if app_env == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
