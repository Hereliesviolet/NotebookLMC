# Langdock-Integration

Langdock ist das **einzige** AI-Gateway dieses Projekts. Es gibt keinen
Code-Pfad, der direkt mit OpenAI, Anthropic oder einem anderen
Modell-Provider spricht - jeder Aufruf läuft über `LangdockClient`
(`apps/api/app/langdock/client.py`, gespiegelt in `apps/worker/app/langdock/client.py`).

## Verwendete Endpunkte

| Zweck | Endpunkt | Genutzt für |
| --- | --- | --- |
| Anthropic-kompatibel | `LANGDOCK_ANTHROPIC_BASE_URL` (`https://api.langdock.com/anthropic/eu`) | Claude Sonnet 5, Claude Haiku |
| OpenAI-kompatibel | `EMBEDDING_BASE_URL` (`https://api.langdock.com/openai/eu/v1`) | Embeddings (`text-embedding-ada-002`) |

Die Anbindung nutzt bewusst die offiziellen `anthropic`- und `openai`-Python-SDKs
mit überschriebener `base_url`, da beide Endpunkte laut Projektvorgabe
API-kompatibel zu den jeweiligen Original-APIs sind.

## Modell-IDs ermitteln (TODO für den Betrieb)

`LANGDOCK_PRIMARY_MODEL` (Claude Sonnet 5) und `LANGDOCK_FAST_MODEL` (Claude
Haiku) sind in `.env.example` **absichtlich leer**. Es wurden keine
Modell-IDs erfunden. Um die echten IDs zu ermitteln:

1. Im Langdock-Dashboard unter API-Zugriff / Modelle nachsehen, oder
2. Den Modell-Listen-Endpunkt der Langdock Agent API abfragen (Basis-URL:
   `LANGDOCK_AGENT_BASE_URL`, siehe `.env.example`) und die gewünschten
   Claude-Sonnet-5-/Claude-Haiku-Varianten heraussuchen.

Die ermittelten IDs kommen ausschließlich in die `.env`-Datei - niemals in
den Code. `LangdockClient._model_for()` wirft einen klaren Fehler, wenn eine
ID fehlt, statt eine falsche ID zu raten.

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

## Streaming (vorbereitet, nicht aktiv genutzt)

`LangdockClient.stream()` kapselt einen Streaming-Aufruf über die
Anthropic-kompatible API. Der aktuelle Chat-Endpoint gibt eine einzelne,
validierte JSON-Antwort zurück (nötig für die Citation Validation vor dem
Ausliefern) - Streaming wäre ein sinnvoller nächster Schritt für die
Chat-UX, ist aber nicht Teil des MVP.
