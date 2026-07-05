"""Single Langdock gateway client (architecture doc §17.1).

Every AI call in this app goes through this class - no direct calls to
OpenAI/Anthropic/etc anywhere else in the codebase. It wraps two
Langdock-provided, provider-compatible endpoints:

  - Anthropic-compatible Messages API -> Claude Sonnet 5 / Claude Haiku
  - OpenAI-compatible Embeddings API  -> text-embedding-ada-002

Model ids (`LANGDOCK_PRIMARY_MODEL`, `LANGDOCK_FAST_MODEL`) are read
exclusively from settings/.env - never hardcoded (see docs/langdock.md for
how to discover them via the Langdock model list endpoint).
"""
import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from anthropic import Anthropic, APIStatusError
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ModelTier = Literal["sonnet", "haiku"]


@dataclass
class LangdockUsage:
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    status_code: int | None = None
    error_message: str | None = None


@dataclass
class LangdockTextResponse:
    text: str
    usage: LangdockUsage


@dataclass
class LangdockEmbeddingResponse:
    vectors: list[list[float]]
    usage: LangdockUsage = field(default_factory=lambda: LangdockUsage(model=""))


class RateLimitedError(Exception):
    """Raised on Langdock 429s so tenacity can retry with backoff."""


class LangdockClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings

        if not settings.langdock_api_key:
            logger.warning("LANGDOCK_API_KEY is empty - Langdock calls will fail until it is set in .env")

        self._anthropic = Anthropic(
            api_key=settings.langdock_api_key or "unset",
            base_url=settings.langdock_anthropic_base_url,
        )
        self._openai = OpenAI(
            api_key=settings.langdock_api_key or "unset",
            base_url=settings.embedding_base_url,
        )

    def _model_for(self, tier: ModelTier) -> str:
        model = self._settings.langdock_primary_model if tier == "sonnet" else self._settings.langdock_fast_model
        if not model:
            raise RuntimeError(
                f"No Langdock model id configured for tier={tier!r}. Set LANGDOCK_PRIMARY_MODEL / "
                f"LANGDOCK_FAST_MODEL in .env (see docs/langdock.md for how to discover valid ids)."
            )
        return model

    def _retry_decorator(self):
        backoffs = self._settings.retry_backoff_seconds or [5, 15, 30, 60]
        return retry(
            reraise=True,
            retry=retry_if_exception_type(RateLimitedError),
            stop=stop_after_attempt(len(backoffs) + 1),
            wait=wait_fixed(backoffs[0]) if len(set(backoffs)) == 1 else _variable_wait(backoffs),
        )

    def _generate(self, tier: ModelTier, system: str, user_message: str, max_tokens: int) -> LangdockTextResponse:
        model = self._model_for(tier)
        started = time.monotonic()

        @self._retry_decorator()
        def _call():
            try:
                return self._anthropic.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_message}],
                )
            except APIStatusError as exc:
                if exc.status_code == 429:
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = _call()
        latency_ms = int((time.monotonic() - started) * 1000)

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        usage = LangdockUsage(
            model=model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            total_tokens=(getattr(response.usage, "input_tokens", 0) or 0)
            + (getattr(response.usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
            status_code=200,
        )
        return LangdockTextResponse(text=text, usage=usage)

    def generate_sonnet(self, system: str, user_message: str, max_tokens: int = 2048) -> LangdockTextResponse:
        """Claude Sonnet 5 - final answers, complex analysis (architecture doc §7.1)."""
        return self._generate("sonnet", system, user_message, max_tokens)

    def generate_haiku(self, system: str, user_message: str, max_tokens: int = 512) -> LangdockTextResponse:
        """Claude Haiku - intent detection, query rewrite, short summaries (§7.2)."""
        return self._generate("haiku", system, user_message, max_tokens)

    def structured_output(
        self, tier: ModelTier, system: str, user_message: str, max_tokens: int = 2048
    ) -> tuple[dict[str, Any], LangdockUsage]:
        """Calls the given model tier and parses the response as JSON.

        The prompts in packages/prompts/ all instruct the model to return
        JSON only, so this is a thin, forgiving wrapper (strips markdown
        code fences if the model adds them anyway).
        """
        response = self._generate(tier, system, user_message, max_tokens)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw), response.usage
        except json.JSONDecodeError as exc:
            raise ValueError(f"Langdock model did not return valid JSON: {exc}\nRaw: {raw[:500]}") from exc

    def embed(self, texts: list[str]) -> LangdockEmbeddingResponse:
        """Langdock OpenAI-compatible embeddings (architecture doc §7.3).

        Always uses EMBEDDING_MODEL (text-embedding-ada-002) and never
        Sonnet/Haiku - embeddings are a separate task class in the model
        router (see model_router.py).
        """
        settings = self._settings
        started = time.monotonic()

        @self._retry_decorator()
        def _call():
            try:
                return self._openai.embeddings.create(
                    model=settings.embedding_model,
                    input=texts,
                    encoding_format=settings.embedding_encoding_format,
                )
            except Exception as exc:  # openai SDK raises its own RateLimitError subclass
                if "429" in str(exc) or exc.__class__.__name__ == "RateLimitError":
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = _call()
        latency_ms = int((time.monotonic() - started) * 1000)
        vectors = [item.embedding for item in response.data]
        usage = LangdockUsage(
            model=settings.embedding_model,
            input_tokens=getattr(response.usage, "prompt_tokens", None) if response.usage else None,
            total_tokens=getattr(response.usage, "total_tokens", None) if response.usage else None,
            latency_ms=latency_ms,
            status_code=200,
        )
        return LangdockEmbeddingResponse(vectors=vectors, usage=usage)

    def stream(self, tier: ModelTier, system: str, user_message: str, max_tokens: int = 2048):
        """Streaming Sonnet/Haiku responses.

        Prepared per architecture doc §17.1 but not consumed by the MVP
        chat endpoint yet (which returns a single validated JSON payload).
        Wire this up to Server-Sent Events on /chat once streaming UX is
        prioritized.
        """
        model = self._model_for(tier)
        with self._anthropic.messages.stream(
            model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user_message}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def usage_export(self) -> list[dict[str, Any]]:
        """Optional Langdock Usage Export API (architecture doc §4, §17.2).

        Disabled by default (LANGDOCK_USAGE_EXPORT_ENABLED=false). No
        documented request/response shape is given in the architecture doc,
        so this stays a TODO until that's confirmed against the real API.
        """
        if not self._settings.langdock_usage_export_enabled:
            raise RuntimeError("Langdock usage export is disabled (LANGDOCK_USAGE_EXPORT_ENABLED=false)")
        raise NotImplementedError("TODO: implement once the Langdock Usage Export API contract is confirmed")


def _variable_wait(backoffs: list[int]):
    from tenacity.wait import wait_base

    class _Wait(wait_base):
        def __call__(self, retry_state) -> float:
            attempt = retry_state.attempt_number - 1
            return backoffs[min(attempt, len(backoffs) - 1)]

    return _Wait()


@lru_cache
def get_langdock_client() -> LangdockClient:
    return LangdockClient()
