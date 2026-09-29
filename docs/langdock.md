# Langdock integration

Langdock is the only AI gateway of this project. No code path talks to OpenAI,
Anthropic or another model provider directly; every call goes through
`LangdockClient` (`apps/api/app/langdock/client.py`, mirrored in
`apps/worker/app/langdock/client.py`).

## Endpoints

| Kind | Setting | Used for |
| --- | --- | --- |
| Anthropic-compatible | `LANGDOCK_ANTHROPIC_BASE_URL` (`https://api.langdock.com/anthropic/eu/v1`) | Claude Sonnet (answers, studio), Claude Haiku (intent, rewrite), Claude vision (OCR fallback in the worker) |
| OpenAI-compatible | `EMBEDDING_BASE_URL` (`https://api.langdock.com/openai/eu/v1`) | Embeddings (`text-embedding-ada-002`) |

The client uses the official `anthropic` and `openai` Python SDKs with an
overridden `base_url`, because both Langdock endpoints are API-compatible with
the originals.

### The `/v1` suffix

Langdock documents the Anthropic-compatible base URL with a `/v1` suffix. The
`anthropic` SDK appends `/v1/messages` to its `base_url` on every call, so
passing the URL unchanged would produce `.../v1/v1/messages`, which Langdock
answers with a 404. `_anthropic_sdk_base_url()` in the client strips a trailing
`/v1` before the URL is handed to the SDK. The variable can therefore be set
the way Langdock documents it.

## Model ids

`LANGDOCK_PRIMARY_MODEL` (Claude Sonnet) and `LANGDOCK_FAST_MODEL` (Claude
Haiku) default in `.env.example` to values from one Langdock workspace:

```env
LANGDOCK_PRIMARY_MODEL=claude-sonnet-4-6-default
LANGDOCK_FAST_MODEL=claude-haiku-4-5@20251001
```

These ids are not universal. Availability and naming depend on the workspace
and region, and "4.6" is just what this project is configured with. To find the
ids of your workspace:

1. Look in the Langdock dashboard under API access / models, or
2. query the model list of the Langdock Agent API (base URL
   `LANGDOCK_AGENT_BASE_URL`), or
3. send a minimal `messages.create()` call with a guessed id; on an invalid id
   Langdock answers with 400 or 404 and usually lists the available ids in
   the error text.

Model ids belong in `.env`, never in code. `LangdockClient._model_for()` raises
an explicit error if an id is missing instead of guessing one.

## Extended thinking

`LANGDOCK_ENABLE_EXTENDED_THINKING` only affects
`LangdockClient.generate_sonnet()`. When true, that method sends
`thinking={"type": "enabled", "budget_tokens": 4096}` and raises `max_tokens`
by the budget, since the Anthropic API requires `max_tokens` to be larger than
`budget_tokens`. The chat and studio flows call `tool_output()` and
`generate_structured()`, not `generate_sonnet()`, so the flag currently has no
effect on them. Whether a given model accepts the `budget_tokens` mode or needs
a newer thinking variant depends on the model.

## Prompts

Prompt texts and tool schemas are files in `packages/prompts/`, loaded at run
time by `prompts_loader.py`:

- `system_final_answer.md` and `final_answer_tool_schema.json` for chat answers
  (`output_schema.json` documents the same response shape)
- `haiku_intent_detection.md`, `haiku_query_rewrite.md`
- `studio_<type>.md` and `studio_<type>_tool_schema.json` for each of the seven
  studio artifact types

With Docker, `packages/prompts` is mounted read-only into `api` and `worker`
(see `docker-compose.yml`). Outside Docker, the loader finds the directory
relative to the repository root, or takes `PROMPTS_DIR`.

## Retries and usage tracking

- On HTTP 429, `LangdockClient` retries with the waits from
  `LANGDOCK_RETRY_BACKOFF_SECONDS` (default `5,15,30,60`). The waits use
  `asyncio.sleep` in the API, so they do not block the event loop.
- `langdock_requests` stores model, latency and token counts for chat answers
  (best effort: a failed write does not fail the answer). Studio calls and
  embeddings are not recorded there.
- `LangdockClient.usage_export()` is a placeholder for the Langdock Usage
  Export API and is not implemented.

## Prompt caching

Anthropic prompt caching (`cache_control: {"type": "ephemeral"}` on a content
block) works through Langdock's Anthropic-compatible gateway. It was checked by
hand against the live API: a large system block returned
`cache_creation_input_tokens` on the first call and `cache_read_input_tokens`
with the same number on the following calls. Langdock's published OpenAPI
schema does not list `cache_control`, so this behaviour is observed, not
documented.

It is used for studio generation (`cache_user_message=True` in
`studio/service.py`): the notebook-wide context is identical for all artifact
types and retries of the same notebook until a source changes. It is not used
for chat, because the retrieved context differs per question and a cache write
costs about 25 percent more input tokens than a normal call.

## Streaming

`LangdockClient.stream()` wraps a streaming call. The chat endpoint does not use
it: it returns one validated JSON response, because citations are validated
before anything is sent to the client.
