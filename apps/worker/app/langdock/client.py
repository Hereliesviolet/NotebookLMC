"""Langdock gateway client - worker side.

Mirrors apps/api/app/langdock/client.py (see docs/architecture.md on why this is
duplicated rather than imported from a shared package). The worker mainly
needs `embed()`; `generate_haiku`/`generate_sonnet` are kept available for
future worker-side jobs that need LLM calls.
"""

import base64
import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from anthropic import Anthropic, APIStatusError
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_base

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ModelTier = Literal["sonnet", "haiku"]

# Siehe apps/api/app/langdock/client.py fuer die Begruendung (gegen die echte
# Langdock-API verifiziert).
EXTENDED_THINKING_BUDGET_TOKENS = 4096


def _anthropic_sdk_base_url(configured_base_url: str) -> str:
    """Normalisiert LANGDOCK_ANTHROPIC_BASE_URL fuer das Anthropic-Python-SDK.

    Das SDK haengt bei jedem Messages-Call selbst fest "/v1/messages" an die
    base_url an. Ein bereits vorhandenes "/v1"-Suffix in
    LANGDOCK_ANTHROPIC_BASE_URL wuerde sonst zu ".../v1/v1/messages" und
    einem 404 bei Langdock fuehren.
    """
    trimmed = configured_base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        trimmed = trimmed[: -len("/v1")]
    return trimmed


@dataclass
class LangdockUsage:
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    status_code: int | None = None
    error_message: str | None = None
    stop_reason: str | None = None


@dataclass
class LangdockTextResponse:
    text: str
    usage: LangdockUsage


@dataclass
class LangdockEmbeddingResponse:
    vectors: list[list[float]]
    usage: LangdockUsage = field(default_factory=lambda: LangdockUsage(model=""))


class RateLimitedError(Exception):
    pass


class _VariableWait(wait_base):
    def __init__(self, backoffs: list[int]) -> None:
        self._backoffs = backoffs

    def __call__(self, retry_state) -> float:
        attempt = retry_state.attempt_number - 1
        return self._backoffs[min(attempt, len(self._backoffs) - 1)]


class LangdockClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings

        if not settings.langdock_api_key:
            logger.warning(
                "LANGDOCK_API_KEY is empty - Langdock calls will fail until it is set in .env"
            )

        self._anthropic = Anthropic(
            api_key=settings.langdock_api_key or "unset",
            base_url=_anthropic_sdk_base_url(settings.langdock_anthropic_base_url),
        )
        self._openai = OpenAI(
            api_key=settings.langdock_api_key or "unset", base_url=settings.embedding_base_url
        )

    def _model_for(self, tier: ModelTier) -> str:
        model = (
            self._settings.langdock_primary_model
            if tier == "sonnet"
            else self._settings.langdock_fast_model
        )
        if not model:
            raise RuntimeError(
                f"No Langdock model id configured for tier={tier!r}. Set LANGDOCK_PRIMARY_MODEL / "
                f"LANGDOCK_FAST_MODEL in .env (see docs/langdock.md)."
            )
        return model

    def _retry_decorator(self):
        backoffs = self._settings.retry_backoff_seconds or [5, 15, 30, 60]
        return retry(
            reraise=True,
            retry=retry_if_exception_type(RateLimitedError),
            stop=stop_after_attempt(len(backoffs) + 1),
            wait=_VariableWait(backoffs),
        )

    def _generate(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        max_tokens: int,
        enable_thinking: bool = False,
    ) -> LangdockTextResponse:
        model = self._model_for(tier)
        started = time.monotonic()

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
        }
        if enable_thinking:
            create_kwargs["max_tokens"] = max_tokens + EXTENDED_THINKING_BUDGET_TOKENS
            create_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": EXTENDED_THINKING_BUDGET_TOKENS,
            }

        @self._retry_decorator()
        def _call():
            try:
                return self._anthropic.messages.create(**create_kwargs)
            except APIStatusError as exc:
                if exc.status_code == 429:
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = _call()
        latency_ms = int((time.monotonic() - started) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = LangdockUsage(
            model=model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            latency_ms=latency_ms,
            status_code=200,
            stop_reason=getattr(response, "stop_reason", None),
        )
        return LangdockTextResponse(text=text, usage=usage)

    def generate_haiku(
        self, system: str, user_message: str, max_tokens: int = 512
    ) -> LangdockTextResponse:
        return self._generate("haiku", system, user_message, max_tokens)

    def generate_sonnet(
        self, system: str, user_message: str, max_tokens: int = 2048
    ) -> LangdockTextResponse:
        return self._generate(
            "sonnet",
            system,
            user_message,
            max_tokens,
            enable_thinking=self._settings.langdock_enable_extended_thinking,
        )

    def structured_output(
        self, tier: ModelTier, system: str, user_message: str, max_tokens: int = 2048
    ) -> tuple[dict[str, Any], LangdockUsage]:
        response = self._generate(tier, system, user_message, max_tokens)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw), response.usage
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Langdock model did not return valid JSON: {exc}\nRaw: {raw[:500]}"
            ) from exc

    def extract_text_from_image(
        self, image_bytes: bytes, media_type: str = "image/jpeg", max_tokens: int = 4096
    ) -> LangdockTextResponse:
        """OCR fallback for scanned PDF pages without a text layer via Claude
        Vision (no Tesseract dependency - stays consistent with "all AI calls
        go through the Langdock client").
        """
        response = self._vision_call(max_tokens, image_bytes, media_type)
        if response.usage.stop_reason == "max_tokens":
            retry_max_tokens = max_tokens * 2
            logger.warning(
                "Vision OCR output truncated (stop_reason=max_tokens), retrying once with max_tokens=%s",
                retry_max_tokens,
            )
            response = self._vision_call(retry_max_tokens, image_bytes, media_type)
        return response

    def _vision_call(
        self, max_tokens: int, image_bytes: bytes, media_type: str
    ) -> LangdockTextResponse:
        model = self._model_for("sonnet")
        started = time.monotonic()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": "Du extrahierst Text aus gescannten Dokumentseiten fuer eine Volltextsuche.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extrahiere den vollständigen Text dieser Dokumentseite exakt und "
                                "vollständig, ohne Kommentare oder Zusammenfassung. Gib nur den "
                                "erkannten Text zurück."
                            ),
                        },
                    ],
                }
            ],
        }

        @self._retry_decorator()
        def _call():
            try:
                return self._anthropic.messages.create(**create_kwargs)
            except APIStatusError as exc:
                if exc.status_code == 429:
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = _call()
        latency_ms = int((time.monotonic() - started) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = LangdockUsage(
            model=model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            latency_ms=latency_ms,
            status_code=200,
            stop_reason=getattr(response, "stop_reason", None),
        )
        return LangdockTextResponse(text=text, usage=usage)

    def embed(self, texts: list[str]) -> LangdockEmbeddingResponse:
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
            except Exception as exc:
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


@lru_cache
def get_langdock_client() -> LangdockClient:
    return LangdockClient()
