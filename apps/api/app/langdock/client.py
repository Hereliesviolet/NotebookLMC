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
import base64
import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

import httpx
from anthropic import Anthropic, APIStatusError
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ModelTier = Literal["sonnet", "haiku"]

# Extended-Thinking-Budget fuer Sonnet-Aufrufe mit LANGDOCK_ENABLE_EXTENDED_THINKING=true.
# max_tokens muss laut Anthropic-API strikt groesser als budget_tokens sein, daher wird es
# in _generate() um dieses Budget erhoeht (siehe generate_sonnet()).
EXTENDED_THINKING_BUDGET_TOKENS = 4096


def _anthropic_sdk_base_url(configured_base_url: str) -> str:
    """Normalisiert LANGDOCK_ANTHROPIC_BASE_URL fuer das Anthropic-Python-SDK.

    Das SDK haengt bei jedem Messages-Call selbst fest "/v1/messages" an die
    base_url an (siehe anthropic._base_client.BaseClient._prepare_url). Ein in
    LANGDOCK_ANTHROPIC_BASE_URL bereits enthaltenes "/v1"-Suffix (so wie es
    Langdock inzwischen als vollstaendige Basis-URL dokumentiert) wuerde sonst
    zu ".../v1/v1/messages" und einem 404 bei Langdock fuehren - gegen die
    echte Langdock-API verifiziert. Deshalb wird ein vorhandenes "/v1"-Suffix
    hier entfernt, bevor die base_url an das SDK uebergeben wird.
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
    """Raised on Langdock 429s so tenacity can retry with backoff."""


class ResponseTruncatedError(Exception):
    """Raised when a structured_output() response was cut off before completion.

    Triggered either by Anthropic's stop_reason=="max_tokens", or by a
    JSON parse failure on the (in that case near-certainly truncated) raw
    text - distinct from RateLimitedError/auth/network failures so callers
    can offer a specific "answer too long" message instead of a generic one.
    """

    def __init__(self, message: str, stop_reason: str | None, usage: "LangdockUsage | None" = None) -> None:
        super().__init__(message)
        self.stop_reason = stop_reason
        self.usage = usage


class ImageGenerationError(Exception):
    """Raised by generate_agent_image() when the Langdock agent call fails,
    times out, or its response doesn't contain an image_generation
    tool-result (e.g. the agent used a "bash"/code-execution tool to draw
    the image itself instead of calling the image generation tool - observed
    live for ambiguous prompts before the agent's Image Generation
    capability was enabled).
    """


# Bildgenerierung ueber einen Langdock-Agenten dauert im Test 40-70s (deutlich
# laenger als die Text-Endpunkte) - grosszuegiges Timeout, kein Retry-on-429
# hier (die Agent-API ist ein anderer Endpoint als die Messages-API).
_AGENT_IMAGE_TIMEOUT_SECONDS = 120.0


class LangdockClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings

        if not settings.langdock_api_key:
            logger.warning("LANGDOCK_API_KEY is empty - Langdock calls will fail until it is set in .env")

        self._anthropic = Anthropic(
            api_key=settings.langdock_api_key or "unset",
            base_url=_anthropic_sdk_base_url(settings.langdock_anthropic_base_url),
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

    def _call_messages(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        max_tokens: int,
        enable_thinking: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> tuple[Any, LangdockUsage]:
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
            create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": EXTENDED_THINKING_BUDGET_TOKENS}
        if tools:
            create_kwargs["tools"] = tools
        if tool_choice:
            create_kwargs["tool_choice"] = tool_choice

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
        usage = LangdockUsage(
            model=model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            total_tokens=(getattr(response.usage, "input_tokens", 0) or 0)
            + (getattr(response.usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
            status_code=200,
            stop_reason=getattr(response, "stop_reason", None),
        )
        return response, usage

    def _generate(
        self, tier: ModelTier, system: str, user_message: str, max_tokens: int, enable_thinking: bool = False
    ) -> LangdockTextResponse:
        response, usage = self._call_messages(tier, system, user_message, max_tokens, enable_thinking=enable_thinking)
        # Bei aktiviertem Thinking enthaelt response.content zusaetzlich einen
        # thinking-Block vor dem eigentlichen Text - hier bewusst ignoriert,
        # da nur "text"-Bloecke als Antwort zaehlen.
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return LangdockTextResponse(text=text, usage=usage)

    def generate_sonnet(self, system: str, user_message: str, max_tokens: int = 2048) -> LangdockTextResponse:
        """Claude Sonnet 5 - final answers, complex analysis (architecture doc §7.1)."""
        return self._generate(
            "sonnet", system, user_message, max_tokens, enable_thinking=self._settings.langdock_enable_extended_thinking
        )

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
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            # A malformed JSON body is near-certainly caused by the response
            # being cut off mid-generation - treat it as truncation even if
            # stop_reason wasn't (yet) reported as "max_tokens".
            raise ResponseTruncatedError(
                f"Langdock model returned invalid/truncated JSON (stop_reason={response.usage.stop_reason!r}): "
                f"{exc}\nRaw: {raw[:500]}",
                stop_reason=response.usage.stop_reason,
                usage=response.usage,
            ) from exc
        if response.usage.stop_reason == "max_tokens":
            raise ResponseTruncatedError(
                f"Langdock model response was cut off at max_tokens={max_tokens} (stop_reason=max_tokens).",
                stop_reason="max_tokens",
                usage=response.usage,
            )
        return parsed, response.usage

    def generate_structured(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        tool_name: str,
        tool_schema: dict[str, Any],
        max_tokens: int,
        tool_description: str = "",
    ) -> tuple[dict[str, Any], LangdockUsage]:
        """Forces the model to answer via native Anthropic tool-use (`tool_choice`)
        instead of a free-text "return JSON" instruction.

        Anthropic parses/validates the tool-call arguments server-side against
        `tool_schema`, so `block.input` is already a Python dict - no
        `json.loads()` on model-generated text, which structurally avoids the
        broken-escaping failure class free-text JSON is prone to (unescaped
        quotes/newlines from quoted source material breaking the JSON string).
        Generalized so chat (tool_output()) and the Studio artifacts
        (summary/faq/timeline/briefing) share one implementation.
        """
        tool = {"name": tool_name, "description": tool_description, "input_schema": tool_schema}
        tool_choice = {"type": "tool", "name": tool_name}
        response, usage = self._call_messages(
            tier, system, user_message, max_tokens, tools=[tool], tool_choice=tool_choice
        )
        if usage.stop_reason == "max_tokens":
            raise ResponseTruncatedError(
                f"Langdock tool-call response was cut off at max_tokens={max_tokens} (stop_reason=max_tokens).",
                stop_reason="max_tokens",
                usage=usage,
            )
        tool_use_blocks = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        if not tool_use_blocks:
            raise ValueError(
                f"Langdock model did not return a tool_use block for tool={tool_name!r} "
                f"(stop_reason={usage.stop_reason!r})"
            )
        tool_input = tool_use_blocks[0].input
        if not isinstance(tool_input, dict):
            raise ValueError(f"Langdock tool_use.input for tool={tool_name!r} was not a JSON object: {tool_input!r}")
        return tool_input, usage

    def tool_output(
        self, tier: ModelTier, system: str, user_message: str, tool: dict[str, Any], max_tokens: int
    ) -> tuple[dict[str, Any], LangdockUsage]:
        """Chat-answer entry point (apps/api/app/chat/service.py) - thin wrapper
        around generate_structured() taking an already-assembled tool dict
        (e.g. loaded from final_answer_tool_schema.json via prompts_loader.py).
        """
        return self.generate_structured(
            tier,
            system,
            user_message,
            tool_name=tool["name"],
            tool_schema=tool["input_schema"],
            max_tokens=max_tokens,
            tool_description=tool.get("description", ""),
        )

    def generate_agent_image(self, agent_id: str, prompt: str) -> bytes:
        """Calls a Langdock Agent (with the "Image Generation" capability
        enabled in the Langdock dashboard) and returns the generated PNG as
        raw bytes.

        Verified request/response contract (apps/api/app/studio/infographic_image.py):
        POST {LANGDOCK_AGENT_BASE_URL}/chat/completions with
        {"agentId", "messages": [...], "imageResponseFormat": "b64_json"}.
        The response's `result` is a list of turns; the image is nested in
        the turn with role="tool" whose content[0].toolName=="image_generation".
        Only that turn is accepted - an agent can fall back to a "bash" tool
        and draw the image itself via PIL for ambiguous prompts, which must
        not be silently treated as a valid image result.
        """
        url = f"{self._settings.langdock_agent_base_url.rstrip('/')}/chat/completions"
        body = {
            "agentId": agent_id,
            "messages": [{"id": "msg_1", "role": "user", "parts": [{"type": "text", "text": prompt}]}],
            "imageResponseFormat": "b64_json",
        }
        started = time.monotonic()
        try:
            response = httpx.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {self._settings.langdock_api_key}"},
                timeout=_AGENT_IMAGE_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ImageGenerationError(f"Langdock-Agent-Aufruf zur Bildgenerierung fehlgeschlagen: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ImageGenerationError(f"Langdock-Agent-Antwort war kein gueltiges JSON: {exc}") from exc

        base64_png = _extract_agent_image_generation_base64(payload)
        logger.info("Langdock agent image generation (agent_id=%s) took %sms", agent_id, latency_ms)
        try:
            return base64.b64decode(base64_png)
        except (ValueError, TypeError) as exc:
            raise ImageGenerationError(f"Base64-Bilddaten der Agent-Antwort konnten nicht dekodiert werden: {exc}") from exc

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


def _extract_agent_image_generation_base64(payload: dict[str, Any]) -> str:
    """Walks the Langdock Agent chat/completions response's `result` turns
    and returns the base64 PNG from the first role="tool" turn whose
    content[0].toolName=="image_generation". Raises ImageGenerationError if
    no such turn exists (e.g. the agent used a "bash" tool instead) or if
    that turn's images array is empty.
    """
    turns = payload.get("result")
    if not isinstance(turns, list):
        raise ImageGenerationError(f"Unerwartetes Antwortformat vom Langdock-Agenten: kein 'result'-Array: {payload!r}")

    for turn in turns:
        if not isinstance(turn, dict) or turn.get("role") != "tool":
            continue
        content = turn.get("content")
        if not isinstance(content, list) or not content:
            continue
        first = content[0]
        if not isinstance(first, dict):
            continue
        if first.get("type") != "tool-result" or first.get("toolName") != "image_generation":
            continue
        images = (((first.get("output") or {}).get("value") or {}).get("images")) or []
        if not images or not isinstance(images[0], dict) or not images[0].get("base64"):
            raise ImageGenerationError(
                "Der Langdock-Agent hat ein image_generation-Tool-Result ohne Bilddaten geliefert."
            )
        return images[0]["base64"]

    raise ImageGenerationError(
        "Der Langdock-Agent hat kein image_generation-Tool-Result geliefert (moeglicherweise wurde stattdessen "
        "ein anderes Tool wie 'bash' genutzt) - keine Bilddaten zum Extrahieren gefunden."
    )


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
