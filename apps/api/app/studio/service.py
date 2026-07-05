"""Studio artifact generation (summary/faq/timeline/briefing, architecture
doc §19/§26.5): notebook-wide context -> Sonnet tool-use -> upsert into
studio_artifacts. Same building blocks as chat/service.py, but over
notebook-wide context instead of query-based retrieval, and always exactly
one persisted row per (notebook_id, type).
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import models
from app.langdock.client import ResponseTruncatedError, get_langdock_client
from app.langdock.prompts_loader import load_prompt, load_tool_schema
from app.studio.context import build_notebook_wide_context

logger = get_logger(__name__)

STUDIO_TYPES = ("summary", "faq", "timeline", "briefing", "quiz", "mindmap", "infographic")

_PROMPT_NAMES = {
    "summary": "studio_summary",
    "faq": "studio_faq",
    "timeline": "studio_timeline",
    "briefing": "studio_briefing",
    "quiz": "studio_quiz",
    "mindmap": "studio_mindmap",
    "infographic": "studio_infographic",
}
_TOOL_SCHEMA_NAMES = {
    "summary": "studio_summary_tool_schema",
    "faq": "studio_faq_tool_schema",
    "timeline": "studio_timeline_tool_schema",
    "briefing": "studio_briefing_tool_schema",
    "quiz": "studio_quiz_tool_schema",
    "mindmap": "studio_mindmap_tool_schema",
    "infographic": "studio_infographic_tool_schema",
}

# Sonnet's tool-use occasionally stringifies a nested array field instead of
# returning real JSON (observed live for `faq.items`) even though the tool's
# input_schema declares it as an array - unlike a top-level parse failure,
# Anthropic's tool-use only guarantees the *overall* tool_use.input is valid
# JSON, not that every nested field actually matches the declared type. When
# the model does this, it's re-serializing that field as free-text JSON
# itself, which reintroduces the exact broken-quote-escaping failure class
# tool-use was meant to eliminate (e.g. an unescaped `"` inside a quoted
# source excerpt). _normalize_content() re-parses these fields defensively;
# if that also fails, the caller retries the whole generation.
_ARRAY_FIELDS = {
    "faq": ["items"],
    "timeline": ["events"],
    "briefing": ["key_points", "risks", "recommended_actions", "open_questions"],
    "quiz": ["questions"],
    "infographic": ["sections", "stats"],
    # mindmap's only array-shaped field ("root.children", nested two levels
    # deep) isn't a top-level content field, so it isn't covered by
    # _normalize_content()'s flat-field re-parsing below - add a nested-path
    # variant here if testing shows Sonnet stringifying it too.
}


class NoIndexedSourcesError(Exception):
    """No source in this notebook has status='indexed' yet."""


class StudioGenerationError(Exception):
    """Langdock call failed, or the output was truncated/malformed even after retries."""


class _MalformedStudioOutputError(Exception):
    """A declared-array field came back as a string that isn't valid JSON either."""


def _normalize_content(artifact_type: str, content: dict) -> dict:
    for field in _ARRAY_FIELDS.get(artifact_type, []):
        value = content.get(field)
        if isinstance(value, str):
            try:
                content[field] = json.loads(value)
            except json.JSONDecodeError as exc:
                raise _MalformedStudioOutputError(
                    f"field {field!r} was a string instead of an array, and isn't valid JSON either: {exc}"
                ) from exc
    return content


async def generate_artifact(
    db: AsyncSession, notebook_id: str, artifact_type: str, source_ids: list[str] | None = None
) -> models.StudioArtifact:
    if artifact_type not in STUDIO_TYPES:
        raise ValueError(f"Unknown studio artifact type: {artifact_type!r}")

    settings = get_settings()
    client = get_langdock_client()

    context, sources = await build_notebook_wide_context(db, notebook_id, source_ids=source_ids)
    if not sources:
        raise NoIndexedSourcesError("Keine indizierten Quellen in diesem Notebook gefunden.")

    system_prompt = load_prompt(_PROMPT_NAMES[artifact_type])
    user_message = f"Quellenkontext (alle indizierten Quellen dieses Notebooks):\n{context}"

    max_tokens = settings.studio_answer_max_tokens
    content, usage = await _generate_and_validate(client, artifact_type, system_prompt, user_message, max_tokens, notebook_id)

    source_id_list = [str(s.id) for s in sources]
    return await _upsert_artifact(db, notebook_id, artifact_type, content, source_id_list, usage.model)


_MAX_GENERATION_ATTEMPTS = 3


async def _generate_and_validate(client, artifact_type, system_prompt, user_message, max_tokens, notebook_id):
    """Up to 3 Sonnet calls total: retries on truncation (doubled max_tokens)
    and, independently, on a malformed nested-array field (fresh sample at
    the same max_tokens - the failure is stochastic, not budget-related).

    `cache_user_message=True`: `user_message` here *is* the notebook-wide
    context block (see generate_artifact() below) - identical for every
    artifact_type/retry on the same notebook until a source is added/removed.
    Anthropic prompt-caching (`cache_control: {"type": "ephemeral"}`) is
    confirmed to work through Langdock's Anthropic-compatible gateway
    (live-tested against the real API: a second call with the same cached
    block returned `cache_read_input_tokens` equal to the first call's
    `cache_creation_input_tokens`, with `cache_creation_input_tokens=0` on
    the repeat - see docs/langdock.md). This lets a same-notebook re-roll
    ("Neu generieren") or a follow-up artifact within the 5-minute ephemeral
    TTL skip reprocessing the (often large) shared context.
    """
    tool = load_tool_schema(_TOOL_SCHEMA_NAMES[artifact_type])
    attempt_tokens = max_tokens
    last_error: Exception | None = None

    for attempt in range(1, _MAX_GENERATION_ATTEMPTS + 1):
        try:
            content, usage = await client.generate_structured(
                "sonnet",
                system_prompt,
                user_message,
                tool_name=tool["name"],
                tool_schema=tool["input_schema"],
                max_tokens=attempt_tokens,
                tool_description=tool.get("description", ""),
                cache_user_message=True,
            )
        except ResponseTruncatedError as exc:
            last_error = exc
            attempt_tokens = max_tokens * 2
            logger.warning(
                "Studio %s truncated (attempt %s/%s) for notebook=%s, retrying with max_tokens=%s",
                artifact_type,
                attempt,
                _MAX_GENERATION_ATTEMPTS,
                notebook_id,
                attempt_tokens,
            )
            continue
        except Exception as exc:
            raise StudioGenerationError(f"Langdock-Fehler bei der {artifact_type}-Generierung: {exc}") from exc

        try:
            return _normalize_content(artifact_type, content), usage
        except _MalformedStudioOutputError as exc:
            last_error = exc
            logger.warning(
                "Studio %s malformed output (attempt %s/%s) for notebook=%s: %s - retrying",
                artifact_type,
                attempt,
                _MAX_GENERATION_ATTEMPTS,
                notebook_id,
                exc,
            )
            continue

    if isinstance(last_error, ResponseTruncatedError):
        raise StudioGenerationError(
            "Der generierte Inhalt war zu umfangreich und wurde auch nach mehreren Versuchen abgeschnitten - "
            "bitte die Quellenauswahl eingrenzen."
        ) from last_error
    raise StudioGenerationError(
        "Der generierte Inhalt enthielt ein fehlerhaft formatiertes Element und konnte auch nach mehreren "
        "Versuchen nicht korrekt geparst werden - bitte erneut versuchen."
    ) from last_error


async def _upsert_artifact(
    db: AsyncSession, notebook_id: str, artifact_type: str, content: dict, source_id_list: list[str], model: str | None
) -> models.StudioArtifact:
    result = await db.execute(
        select(models.StudioArtifact).where(
            models.StudioArtifact.notebook_id == notebook_id, models.StudioArtifact.type == artifact_type
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.content_json = content
        existing.source_ids_json = source_id_list
        existing.model = model
        await db.commit()
        await db.refresh(existing)
        return existing

    artifact = models.StudioArtifact(
        notebook_id=notebook_id,
        type=artifact_type,
        content_json=content,
        source_ids_json=source_id_list,
        model=model,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def get_artifact(db: AsyncSession, notebook_id: str, artifact_type: str) -> models.StudioArtifact | None:
    result = await db.execute(
        select(models.StudioArtifact).where(
            models.StudioArtifact.notebook_id == notebook_id, models.StudioArtifact.type == artifact_type
        )
    )
    return result.scalar_one_or_none()
