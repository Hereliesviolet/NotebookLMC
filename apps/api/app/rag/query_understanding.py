"""Optional Haiku pre-processing steps (architecture doc §16.1/§16.2).

Both are prepared, working functions but only invoked from chat/service.py
when the corresponding ENABLE_* flag is set - the MVP core flow
(embed -> retrieve -> Sonnet -> validate) works fine without them.
"""
from app.core.logging import get_logger
from app.langdock.client import LangdockClient
from app.langdock.prompts_loader import load_prompt

logger = get_logger(__name__)


def detect_intent(client: LangdockClient, question: str) -> str:
    system = load_prompt("haiku_intent_detection")
    try:
        data, _usage = client.structured_output("haiku", system, question, max_tokens=100)
        return data.get("intent", "unknown")
    except Exception:
        logger.exception("intent detection failed - continuing without it")
        return "unknown"


def rewrite_query(client: LangdockClient, question: str) -> list[str]:
    system = load_prompt("haiku_query_rewrite")
    try:
        data, _usage = client.structured_output("haiku", system, question, max_tokens=300)
        variants = data.get("queries") or data.get("search_variants") or []
        return [v for v in variants if isinstance(v, str)] or [question]
    except Exception:
        logger.exception("query rewrite failed - falling back to the original question")
        return [question]
