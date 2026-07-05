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

from anthropic import AsyncAnthropic, APIStatusError
from openai import AsyncOpenAI
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
    # Anthropic Prompt-Caching (verified working via Langdock, siehe
    # LangdockClient._call_messages docstring auf cache_user_message).
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None


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


class LangdockClient:
    """Async client (architecture doc §17.1 updated for the apps/api async
    migration): apps/api runs a single asyncio event loop per Uvicorn worker
    process, so every Langdock call here uses the SDKs' async variants
    (`AsyncAnthropic`/`AsyncOpenAI`) instead of blocking that loop for the
    call's entire duration. This class is only used within apps/api - the
    worker service (apps/worker) has its own separate, still-synchronous
    LangdockClient (RQ jobs run in plain sync worker processes, not an event
    loop, so there's nothing to block there).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings

        if not settings.langdock_api_key:
            logger.warning("LANGDOCK_API_KEY is empty - Langdock calls will fail until it is set in .env")

        self._anthropic = AsyncAnthropic(
            api_key=settings.langdock_api_key or "unset",
            base_url=_anthropic_sdk_base_url(settings.langdock_anthropic_base_url),
        )
        self._openai = AsyncOpenAI(
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
        """Note: `self._call()` closures below are `async def`, so tenacity's
        `@retry` auto-detects the coroutine function and switches to its
        `AsyncRetrying` implementation (`tenacity.asyncio`), which awaits
        `asyncio.sleep()` between attempts instead of blocking with
        `time.sleep()` - i.e. retries (incl. their backoff waits) never block
        the event loop, since the entire decorated async call (SDK call +
        retry/backoff) runs as a normal awaited coroutine.
        """
        backoffs = self._settings.retry_backoff_seconds or [5, 15, 30, 60]
        return retry(
            reraise=True,
            retry=retry_if_exception_type(RateLimitedError),
            stop=stop_after_attempt(len(backoffs) + 1),
            wait=wait_fixed(backoffs[0]) if len(set(backoffs)) == 1 else _variable_wait(backoffs),
        )

    async def _call_messages(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        max_tokens: int,
        enable_thinking: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        cache_user_message: bool = False,
    ) -> tuple[Any, LangdockUsage]:
        model = self._model_for(tier)
        started = time.monotonic()

        # cache_user_message=True marks the *entire* user_message as an
        # Anthropic prompt-caching breakpoint (`cache_control: {"type":
        # "ephemeral"}` on a content block instead of passing `content` as a
        # plain string) - verified working through Langdock's Anthropic-
        # compatible gateway (see studio/service.py docstring for the live
        # test proving cache_read_input_tokens on a repeated call). Only
        # worth it for callers whose user_message is large and byte-identical
        # across multiple calls (e.g. the Studio notebook-wide context) -
        # otherwise this just adds the ~25% cache-write token premium with no
        # future cache hit to offset it.
        content: Any = (
            [{"type": "text", "text": user_message, "cache_control": {"type": "ephemeral"}}]
            if cache_user_message
            else user_message
        )
        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        }
        if enable_thinking:
            create_kwargs["max_tokens"] = max_tokens + EXTENDED_THINKING_BUDGET_TOKENS
            create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": EXTENDED_THINKING_BUDGET_TOKENS}
        if tools:
            create_kwargs["tools"] = tools
        if tool_choice:
            create_kwargs["tool_choice"] = tool_choice

        @self._retry_decorator()
        async def _call():
            try:
                return await self._anthropic.messages.create(**create_kwargs)
            except APIStatusError as exc:
                if exc.status_code == 429:
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = await _call()
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
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", None),
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", None),
        )
        return response, usage

    async def _generate(
        self, tier: ModelTier, system: str, user_message: str, max_tokens: int, enable_thinking: bool = False
    ) -> LangdockTextResponse:
        response, usage = await self._call_messages(
            tier, system, user_message, max_tokens, enable_thinking=enable_thinking
        )
        # Bei aktiviertem Thinking enthaelt response.content zusaetzlich einen
        # thinking-Block vor dem eigentlichen Text - hier bewusst ignoriert,
        # da nur "text"-Bloecke als Antwort zaehlen.
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return LangdockTextResponse(text=text, usage=usage)

    async def generate_sonnet(self, system: str, user_message: str, max_tokens: int = 2048) -> LangdockTextResponse:
        """Claude Sonnet 5 - final answers, complex analysis (architecture doc §7.1)."""
        return await self._generate(
            "sonnet", system, user_message, max_tokens, enable_thinking=self._settings.langdock_enable_extended_thinking
        )

    async def generate_haiku(self, system: str, user_message: str, max_tokens: int = 512) -> LangdockTextResponse:
        """Claude Haiku - intent detection, query rewrite, short summaries (§7.2)."""
        return await self._generate("haiku", system, user_message, max_tokens)

    async def structured_output(
        self, tier: ModelTier, system: str, user_message: str, max_tokens: int = 2048
    ) -> tuple[dict[str, Any], LangdockUsage]:
        """Calls the given model tier and parses the response as JSON.

        The prompts in packages/prompts/ all instruct the model to return
        JSON only, so this is a thin, forgiving wrapper (strips markdown
        code fences if the model adds them anyway).
        """
        response = await self._generate(tier, system, user_message, max_tokens)
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

    async def generate_structured(
        self,
        tier: ModelTier,
        system: str,
        user_message: str,
        tool_name: str,
        tool_schema: dict[str, Any],
        max_tokens: int,
        tool_description: str = "",
        cache_user_message: bool = False,
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
        response, usage = await self._call_messages(
            tier,
            system,
            user_message,
            max_tokens,
            tools=[tool],
            tool_choice=tool_choice,
            cache_user_message=cache_user_message,
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

    async def tool_output(
        self, tier: ModelTier, system: str, user_message: str, tool: dict[str, Any], max_tokens: int
    ) -> tuple[dict[str, Any], LangdockUsage]:
        """Chat-answer entry point (apps/api/app/chat/service.py) - thin wrapper
        around generate_structured() taking an already-assembled tool dict
        (e.g. loaded from final_answer_tool_schema.json via prompts_loader.py).
        """
        return await self.generate_structured(
            tier,
            system,
            user_message,
            tool_name=tool["name"],
            tool_schema=tool["input_schema"],
            max_tokens=max_tokens,
            tool_description=tool.get("description", ""),
        )

    async def embed(self, texts: list[str]) -> LangdockEmbeddingResponse:
        """Langdock OpenAI-compatible embeddings (architecture doc §7.3).

        Always uses EMBEDDING_MODEL (text-embedding-ada-002) and never
        Sonnet/Haiku - embeddings are a separate task class in the model
        router (see model_router.py). Accepts multiple texts in one call
        (batched) - callers with several queries should pass them all at
        once instead of looping with one text per call.
        """
        settings = self._settings
        started = time.monotonic()

        @self._retry_decorator()
        async def _call():
            try:
                return await self._openai.embeddings.create(
                    model=settings.embedding_model,
                    input=texts,
                    encoding_format=settings.embedding_encoding_format,
                )
            except Exception as exc:  # openai SDK raises its own RateLimitError subclass
                if "429" in str(exc) or exc.__class__.__name__ == "RateLimitError":
                    raise RateLimitedError(str(exc)) from exc
                raise

        response = await _call()
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

    async def stream(self, tier: ModelTier, system: str, user_message: str, max_tokens: int = 2048):
        """Streaming Sonnet/Haiku responses.

        Prepared per architecture doc §17.1 but not consumed by the MVP
        chat endpoint yet (which returns a single validated JSON payload).
        Wire this up to Server-Sent Events on /chat once streaming UX is
        prioritized.
        """
        model = self._model_for(tier)
        async with self._anthropic.messages.stream(
            model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user_message}]
        ) as stream:
            async for text in stream.text_stream:
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
