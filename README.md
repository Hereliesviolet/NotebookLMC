# NotebookLM Clone (self-hosted, Langdock-basiert)

Ein selbst-gehosteter NotebookLM-Klon: Notebooks anlegen, Quellen hochladen,
automatisch parsen/chunken/embedden und mit einem quellengebundenen Chat
inklusive Zitaten befragen. Alle KI-Funktionen laufen ausschließlich über
[Langdock](https://langdock.com) (Claude Sonnet 5, Claude Haiku, OpenAI-
kompatible Embeddings) - es gibt keine direkten Aufrufe an OpenAI, Anthropic
oder andere Modell-Provider.

Weiterführende Dokumentation:

- [`docs/architecture.md`](docs/architecture.md) - Zielarchitektur, Komponenten, Datenmodell
- [`docs/rag-pipeline.md`](docs/rag-pipeline.md) - RAG-Flow im Detail (Retrieval, Context Assembly, Citation Validation)
- [`docs/langdock.md`](docs/langdock.md) - Langdock-Integration, Modell-IDs, Rate Limits
- [`docs/deployment.md`](docs/deployment.md) - Deployment mit Docker Compose + Caddy
- [`docs/security.md`](docs/security.md) - Auth, Zugriffskontrolle, Datenschutz

## Architektur auf einen Blick

```mermaid
flowchart TB
    Browser["User Browser"] --> Caddy["Caddy Reverse Proxy (HTTPS)"]
    Caddy --> Frontend["Next.js Frontend"]
    Caddy --> API["FastAPI Backend"]
    Frontend --> API
    API --> Postgres["PostgreSQL"]
    API --> Redis["Redis (Queue)"]
    API --> MinIO["MinIO (Dateien)"]
    API --> Qdrant["Qdrant (Vektoren)"]
    API --> Langdock["Langdock Gateway"]
    Redis --> Worker["Python Worker"]
    Worker --> Postgres
    Worker --> MinIO
    Worker --> Qdrant
    Worker --> Langdock
    Langdock --> Sonnet["Claude Sonnet 5"]
    Langdock --> Haiku["Claude Haiku"]
    Langdock --> Embeddings["OpenAI Embeddings (ada-002)"]
```

## Voraussetzungen

- Docker & Docker Compose (v2)
- Ein gültiger [Langdock](https://langdock.com) API-Key mit Zugriff auf
  Claude Sonnet 5, Claude Haiku und die OpenAI-kompatiblen Embeddings
- `make` (optional, aber empfohlen - alle Befehle funktionieren auch direkt mit `docker compose`)

## Schnellstart

```bash
# 1. .env aus Vorlage erzeugen
make env
# oder: cp .env.example .env

# 2. .env bearbeiten und mindestens folgende Werte setzen:
#    LANGDOCK_API_KEY=...
#    LANGDOCK_PRIMARY_MODEL=...   (Claude Sonnet 5 Modell-ID, siehe docs/langdock.md)
#    LANGDOCK_FAST_MODEL=...      (Claude Haiku Modell-ID, siehe docs/langdock.md)

# 3. Gesamten Stack bauen und starten
make up
# oder: docker compose up -d --build

# 4. Datenbank-Schema anlegen
make migrate
# oder: docker compose exec api alembic upgrade head

# 5. (optional) Demo-User und Demo-Notebook seeden
make seed
```

Danach ist die Anwendung erreichbar unter:

- Frontend direkt: http://localhost:3000
- API direkt: http://localhost:8000 (Swagger-UI unter `/docs`)
- Über Caddy (eine Domain, lokal ohne echtes TLS-Zertifikat): http://localhost
- MinIO-Konsole: http://localhost:9001
- Qdrant-Dashboard: http://localhost:6333/dashboard

Die Demo-/Dev-Auth loggt beim ersten Frontend-Aufruf automatisch als Demo-User
ein (kein Passwort nötig, siehe [`docs/security.md`](docs/security.md)).

## Nützliche Befehle

```bash
make logs            # Logs aller Services
make api-logs        # Nur API-Logs
make worker-logs      # Nur Worker-Logs
make api-shell        # Shell im API-Container
make db-shell         # psql-Shell auf Postgres
make migrate-autogenerate msg="add xyz"   # neue Alembic-Migration erzeugen
make qdrant-setup     # Qdrant-Collection idempotent (neu) anlegen
make down             # Stack stoppen
make clean            # Stack stoppen und Volumes löschen (DESTRUKTIV)
```

## Projektstruktur

```text
NotebookLMC/
├── apps/
│   ├── frontend/   Next.js 14 (App Router), TypeScript, Tailwind CSS
│   ├── api/        FastAPI, SQLAlchemy (async), Alembic
│   └── worker/      Python RQ-Worker (Parsing, Chunking, Embeddings, Qdrant-Indexierung)
├── packages/
│   ├── prompts/         Prompt-Templates (system_final_answer, Haiku-Prompts, Output-Schema)
│   ├── shared-types/    Referenz-TypeScript-Interfaces für die API-Contracts
│   └── evals/            Golden-Dataset + Eval-Skript-Platzhalter
├── infra/
│   ├── caddy/Caddyfile
│   ├── backup/           Backup-Skripte (Postgres, MinIO, Qdrant)
│   └── scripts/
├── docs/
├── docker-compose.yml
├── .env.example
└── Makefile
```

## MVP-Umfang

Der aktuelle Stand deckt den kompletten Kernflow ab:

1. Notebook anlegen
2. Quelle hochladen (PDF, DOCX, TXT, Markdown, HTML, CSV, XLSX)
3. Datei landet in MinIO, `sources`-Eintrag in Postgres, Job wird über Redis/RQ eingereiht
4. Worker: Text extrahieren → Chunking → Embeddings über Langdock → Vektoren in Qdrant
5. Chatfrage stellen → Query-Embedding → Qdrant-Suche → Context Assembly → Sonnet-5-Antwort → Citation Validation
6. Antwort mit Quellenkarten im Frontend

Studio-Funktionen (Zusammenfassung, FAQ, Timeline, Briefing) sind als
Platzhalter-Endpunkte vorbereitet, aber bewusst nicht Teil des MVP1 (siehe
[`docs/architecture.md`](docs/architecture.md)).

