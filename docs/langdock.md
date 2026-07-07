# Langdock-Integration

Langdock ist das **einzige** AI-Gateway dieses Projekts. Es gibt keinen
Code-Pfad, der direkt mit OpenAI, Anthropic oder einem anderen
Modell-Provider spricht - jeder Aufruf läuft über `LangdockClient`
(`apps/api/app/langdock/client.py`, gespiegelt in `apps/worker/app/langdock/client.py`).

## Verwendete Endpunkte

| Zweck | Endpunkt | Genutzt für |
| --- | --- | --- |
| Anthropic-kompatibel | `LANGDOCK_ANTHROPIC_BASE_URL` (`https://api.langdock.com/anthropic/eu/v1`) | Claude Sonnet 4.6, Claude Haiku |
| OpenAI-kompatibel | `EMBEDDING_BASE_URL` (`https://api.langdock.com/openai/eu/v1`) | Embeddings (`text-embedding-ada-002`) |

Die Anbindung nutzt bewusst die offiziellen `anthropic`- und `openai`-Python-SDKs
mit überschriebener `base_url`, da beide Endpunkte laut Projektvorgabe
API-kompatibel zu den jeweiligen Original-APIs sind.

### Wichtig: `/v1`-Suffix von `LANGDOCK_ANTHROPIC_BASE_URL` und das Anthropic-SDK

Langdock dokumentiert die Anthropic-kompatible Basis-URL inzwischen inklusive
`/v1`-Suffix (`https://api.langdock.com/anthropic/<region>/v1`). Das offizielle
`anthropic`-Python-SDK hängt bei **jedem** Messages-Call selbst fest
`/v1/messages` an seine `base_url` an (siehe `anthropic._base_client`,
Methode `_prepare_url`). Würde man die `/v1`-Basis-URL unverändert an
`Anthropic(base_url=...)` durchreichen, landete der Call bei
`.../v1/v1/messages` - das liefert bei Langdock nachweislich einen `404`.

`LangdockClient` (`apps/api/app/langdock/client.py`,
`apps/worker/app/langdock/client.py`) entfernt daher intern in
`_anthropic_sdk_base_url()` ein eventuell vorhandenes `/v1`-Suffix, bevor die
`base_url` an das SDK übergeben wird. `LANGDOCK_ANTHROPIC_BASE_URL` kann damit
so konfiguriert werden, wie Langdock es dokumentiert (mit `/v1`) - der Code
kompensiert die SDK-Eigenheit automatisch. Gegen die echte Langdock-API
verifiziert (mit und ohne `/v1`-Suffix in der env-Variable).

## Modell-IDs ermitteln

`LANGDOCK_PRIMARY_MODEL` (Claude Sonnet 4.6) und `LANGDOCK_FAST_MODEL` (Claude
Haiku) sind in `.env.example` mit den Beispiel-/Default-Werten aus dem
Langdock-Workspace des Projekt-Betreibers vorbelegt:

```env
LANGDOCK_PRIMARY_MODEL=claude-sonnet-4-6-default
LANGDOCK_FAST_MODEL=claude-haiku-4-5@20251001
```

**Diese IDs sind nicht universell gültig** - Modell-Verfügbarkeit und
-Bezeichner hängen vom jeweiligen Langdock-Workspace und der Region ab.
"4.6" ist ausschließlich der in diesem Projekt aktuell konfigurierte Stand,
keine feste Vorgabe - ein anderer Workspace kann eine andere Sonnet-Version
als aktuellstes/verfügbares Modell führen. Für einen anderen Workspace/eine
andere Region die echten IDs selbst ermitteln:

1. Im Langdock-Dashboard unter API-Zugriff / Modelle nachsehen, oder
2. Den Modell-Listen-Endpunkt der Langdock Agent API abfragen (Basis-URL:
   `LANGDOCK_AGENT_BASE_URL`, siehe `.env.example`) und die gewünschten
   Claude-Sonnet-/Claude-Haiku-Varianten heraussuchen, oder
3. Testweise einen minimalen `messages.create()`-Call mit der vermuteten ID
   gegen `LANGDOCK_ANTHROPIC_BASE_URL` ausführen - bei einer ungültigen ID
   antwortet Langdock mit `400`/`404` und listet im Fehlertext meist die im
   Workspace tatsächlich verfügbaren Modell-IDs auf.

Die ermittelten IDs kommen ausschließlich in die `.env`-Datei - niemals in
den Code. `LangdockClient._model_for()` wirft einen klaren Fehler, wenn eine
ID fehlt, statt eine falsche ID zu raten.

## Claude Extended Thinking (`LANGDOCK_ENABLE_EXTENDED_THINKING`)

Optionales Feature, Default `false` (Verhalten bleibt dann unverändert).
Steuert den `thinking`-Parameter der Anthropic Messages API für den
finalen Sonnet-Aufruf (`LangdockClient.generate_sonnet()`):

- `false` (Default): Sonnet wird wie bisher ohne `thinking`-Parameter
  aufgerufen.
- `true`: Der Aufruf enthält zusätzlich
  `thinking={"type": "enabled", "budget_tokens": 4096}`. `max_tokens` wird
  dafür intern automatisch um dieses Budget erhöht, da die Anthropic-API
  verlangt, dass `max_tokens` strikt größer als `budget_tokens` ist. Die
  Antwort enthält dann vor dem eigentlichen Text-Block zusätzlich einen
  `thinking`-Content-Block; `LangdockClient` filtert beim Zusammensetzen der
  Antwort ausschließlich auf Blöcke vom Typ `text` und überspringt den
  `thinking`-Block automatisch.

Voraussetzung ist ein `anthropic`-Python-SDK, das den `thinking`-Parameter
unterstützt (ab ca. Version 0.49; das Projekt verwendet `anthropic==0.69.0`,
siehe `apps/api/requirements.txt`/`apps/worker/requirements.txt`).

Hinweis: Ob ein konkretes Modell den klassischen `budget_tokens`-Modus
unterstützt oder eine neuere Adaptive-Thinking-Variante verlangt, hängt vom
jeweiligen Modell/Provider-Stand ab - bei einer Ablehnung durch Langdock
(`400`) die Fehlermeldung prüfen, bevor die ID/den Parameter änderst.

## Model Router

`apps/api/app/langdock/model_router.py` (`ModelRouter.select_model()`)
entscheidet anhand des Task-Typs, welches Modell zum Einsatz kommt:

- **Sonnet:** `final_answer`, `complex_summary`, `source_comparison`,
  `contradiction_check`, `legal_reasoning`, `technical_reasoning`, `briefing`
- **Haiku:** `intent_detection`, `query_rewrite`, `title_generation`,
  `followup_questions`, `simple_summary`, `classification`, `reranking`
- **Embedding:** `document_embedding`, `query_embedding` (nie Sonnet/Haiku)

## Prompts

Alle Prompt-Texte liegen zentral unter `packages/prompts/` und werden zur
Laufzeit von `prompts_loader.py` geladen (kein Hardcoding im Python-Code):

- `system_final_answer.md` - System-Prompt für die finale Antwort
- `output_schema.json` - JSON-Schema, das Sonnet einhalten muss
- `haiku_intent_detection.md`, `haiku_query_rewrite.md`, `haiku_reranking.md`

Im Docker-Setup wird `packages/prompts` read-only in `api` und `worker`
gemountet (siehe `docker-compose.yml`).

## Rate Limits, Retries, Kostenkontrolle

- `LangdockClient` retried bei HTTP 429 automatisch mit dem in
  `LANGDOCK_RETRY_BACKOFF_SECONDS` konfigurierten Backoff (Default:
  `5,15,30,60` Sekunden).
- Embedding-Aufrufe laufen im Worker über eine eigene Redis-Queue
  (`embeddings`) mit separater, konfigurierbarer Concurrency
  (`WORKER_EMBEDDING_CONCURRENCY`), damit große Uploads nicht die gesamte
  Job-Verarbeitung blockieren.
- Modell-Routing (Haiku für Utility-Tasks, Sonnet nur für die finale
  Antwort/komplexe Analysen) reduziert Kosten strukturell.
- `langdock_requests`-Tabelle protokolliert pro Sonnet-Aufruf Modell,
  Latenz und Token-Verbrauch (best-effort, blockiert die Antwort nicht bei
  Schreibfehlern) - Basis für spätere Kostenauswertung.
- `LangdockClient.usage_export()` ist als Platzhalter für die optionale
  Langdock Usage Export API vorbereitet (`LANGDOCK_USAGE_EXPORT_ENABLED`),
  aber ohne bestätigten Request/Response-Contract noch nicht implementiert.

## Prompt-Caching (`cache_control`, verifiziert unterstützt)

Anthropic Prompt-Caching (`cache_control: {"type": "ephemeral"}` auf einem
Content-Block) läuft **durch Langdocks Anthropic-kompatible Gateway
hindurch** - live gegen `LANGDOCK_ANTHROPIC_BASE_URL` verifiziert:

1. Erster Call mit einem großen (~18.400 Zeichen) `system`-Content-Block mit
   `cache_control` -> Response-`usage` enthält
   `"cache_creation_input_tokens": 6402, "cache_read_input_tokens": 0`.
2. Zweiter/dritter Call mit demselben Block (wenige Sekunden später) ->
   `"cache_creation_input_tokens": 0, "cache_read_input_tokens": 6402"` -
   voller Cache-Hit.

Das offizielle Langdock-OpenAPI-Schema (`docs.langdock.com` Anthropic
Messages-Endpoint) dokumentiert `cache_control` zwar nicht explizit im
Request-Content-Block-Schema (`RequestTextBlock` hat dort
`additionalProperties: false` ohne `cache_control`-Property) und auch nicht
in seinem `Usage`-Response-Schema - das Feld wird serverseitig aber
offenbar unverändert an Anthropic durchgereicht und die Response gibt die
echten Anthropic-Cache-Felder zurück, statt sie herauszufiltern oder den
Request wegen des zusätzlichen Felds abzulehnen. Die Dokumentation ist hier
also unvollständig/veraltet - die tatsächliche Unterstützung wurde deshalb
empirisch verifiziert statt sich auf die Doku zu verlassen.

**Genutzt in `apps/api/app/studio/service.py`** (`_generate_and_validate()`,
`cache_user_message=True`): der notebook-weite Kontext-Block
(`build_notebook_wide_context()`) ist für alle Studio-Artefakttypen und
Retries desselben Notebooks identisch, bis eine Quelle hinzugefügt/entfernt
wird - ein klassischer Fall für einen wiederholt getroffenen Cache
(TTL 5 Minuten für `ephemeral`). `LangdockClient._call_messages()`
implementiert das generisch über den `cache_user_message`-Parameter
(wickelt den kompletten `user_message`-String stattdessen als
Content-Block-Array mit `cache_control` ein).

**Bewusst nicht aktiviert in `apps/api/app/chat/service.py`**: der dortige
Kontext-Block wird pro Chat-Frage aus dem RAG-Retrieval neu zusammengesetzt
(andere Frage -> andere Embedding-Suche -> i.d.R. andere/anders sortierte
Chunk-Auswahl) und ist damit fast nie byte-identisch zu einem vorherigen
Call, selbst für Folgefragen im selben Notebook. Ein Cache-Write kostet
~25% mehr Input-Tokens als ein normaler Call; ohne realistische
Wiederholungsrate steht dem kein Cache-Hit gegenüber, der das aufwiegt -
für den Chat-Pfad also aktuell kein Netto-Vorteil.

## Streaming (vorbereitet, nicht aktiv genutzt)

`LangdockClient.stream()` kapselt einen Streaming-Aufruf über die
Anthropic-kompatible API. Der aktuelle Chat-Endpoint gibt eine einzelne,
validierte JSON-Antwort zurück (nötig für die Citation Validation vor dem
Ausliefern) - Streaming wäre ein sinnvoller nächster Schritt für die
Chat-UX, ist aber nicht Teil des MVP.
