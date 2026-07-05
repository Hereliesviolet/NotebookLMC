# Architekturkonzept: Self-hosted NotebookLM-Klon mit Langdock

## 1. Zielbild

Wir bauen einen modernen, self-hosted Knowledge-Workspace nach dem Prinzip von NotebookLM.

Das System soll Nutzern ermöglichen, eigene Quellen hochzuladen, automatisch zu verarbeiten, semantisch zu durchsuchen, zusammenzufassen und quellenbasiert mit ihnen zu chatten.

Der Fokus liegt nicht auf einem einfachen „Chat mit PDF“, sondern auf einem produktionsnahen RAG-System mit:

- Quellenverwaltung
- zitierfähigen Antworten
- Dokumentenverständnis
- Notizen
- Zusammenfassungen
- Briefings
- FAQ
- Timelines
- Quellenvergleich
- optionalen Audio-/Podcast-Funktionen
- Docker-basiertem Betrieb auf einem Linux-Server
- Caddy Reverse Proxy
- HTTPS
- Langdock als einzigem AI-Gateway

---

## 2. Architekturgrundsatz

Die Anwendung wird vollständig self-hosted betrieben.

Alle AI-Funktionen laufen ausschließlich über Langdock.

Es gibt keine direkten API-Calls zu:

- OpenAI
- Anthropic
- Voyage
- Jina
- Cohere
- Google
- Mistral
- sonstigen Modellprovidern

Stattdessen gilt:

```text
Unsere App
  -> Langdock
      -> Sonnet 5
      -> Haiku
      -> OpenAI Embeddings
      -> optional Agents API
      -> optional Usage Export
```

Die Produktdatenhaltung bleibt vollständig bei uns.

Langdock wird nicht als primäre Produktdatenbank verwendet, sondern als AI-Gateway.

---

## 3. Was ist self-hosted?

Self-hosted sind:

- Frontend
- Backend API
- Worker
- PostgreSQL
- Redis
- MinIO
- Qdrant
- Caddy
- Authentifizierung
- Rechte-/Rollenmodell
- Notebook-Verwaltung
- Quellenverwaltung
- Uploads
- Dokumentenverarbeitung
- Parsing
- Chunking
- Chatverlauf
- Notizen
- RAG-Orchestrierung
- Retrieval
- Citation Validation
- Monitoring
- Backups
- Evaluation

---

## 4. Was läuft über Langdock?

Über Langdock laufen ausschließlich die AI-Funktionen:

- Claude Sonnet 5 für finale Antworten
- Claude Sonnet 5 für komplexe Analyse
- Claude Sonnet 5 für Quellenvergleich
- Claude Sonnet 5 für hochwertige Briefings
- Claude Haiku für günstige Nebenaufgaben
- Claude Haiku für Intent Detection
- Claude Haiku für Query Rewrite
- Claude Haiku für Follow-up-Fragen
- Claude Haiku für kurze Zusammenfassungen
- Langdock OpenAI Embeddings für semantische Suche
- Langdock Agents API für strukturierte Aufgaben
-  Langdock Usage Export API für Nutzungs-/Kostenmonitoring

---

## 5. High-Level-Architektur

```text
User Browser
    |
    v
Caddy Reverse Proxy
    |
    +-------------------------+
    |                         |
    v                         v
Frontend                 Backend API
Next.js                  FastAPI / NestJS
                              |
         +--------------------+--------------------+
         |                    |                    |
         v                    v                    v
   PostgreSQL               Redis                MinIO
   Metadata                 Queue                Files
         |
         v
       Qdrant
   Vector Search
         ^
         |
Embeddings über Langdock
         ^
         |
Backend / Worker
         |
         v
Langdock API
    |
    +-- Anthropic-compatible API
    |     +-- Claude Sonnet 5
    |     +-- Claude Haiku
    |
    +-- OpenAI-compatible Embedding API
    |     +-- text-embedding-ada-002
    |
    +-- optional Agents API
    |
    +-- optional Usage Export API
```

---

## 6. Zentrale Architekturentscheidung

Die App behält die vollständige Kontrolle über die RAG-Pipeline.

Das bedeutet:

```text
Dokument
  -> self-hosted Upload
  -> self-hosted Storage in MinIO
  -> self-hosted Parsing
  -> self-hosted Chunking
  -> Langdock Embedding API
  -> self-hosted Qdrant
  -> self-hosted Retrieval
  -> optional Langdock Haiku Reranking
  -> Langdock Sonnet 5 Antwortgenerierung
  -> self-hosted Citation Validation
  -> Antwort mit Quellenkarten
```

Nicht gewünscht als Standard:

```text
Dokument
  -> Langdock Knowledge Folder
  -> komplett Langdock-managed RAG
```

Langdock Knowledge Folder kann später optional für Benchmarks oder Sonderfälle genutzt werden, ist aber nicht der Kern der Produktarchitektur.

---

## 7. Modellstrategie

### 7.1 Sonnet 5

Sonnet 5 ist das primäre Qualitätsmodell.

Verwendung:

- finale Chatantworten
- komplexe Quellenanalyse
- technische Analyse
- juristische oder vertragliche Auswertung
- Quellenvergleich
- Widerspruchsanalyse
- Synthese über mehrere Dokumente
- lange Briefings
- hochwertige Studio-Funktionen
- anspruchsvolle Entscheidungsgrundlagen
- komplexe Agentic Workflows

### 7.2 Haiku

Haiku ist das schnelle und kostengünstigere Utility-Modell.

Verwendung:

- Intent Detection
- Query Rewrite
- Notebook-Titel generieren
- Dokumenttyp erkennen
- kurze Source Summary
- Follow-up-Fragen
- einfache Klassifikation
- einfache Extraktion
- UI-Hilfstexte
- Relevanz-Vorbewertung
- optional günstiges LLM-Reranking

Haiku sollte nicht für finale kritische Antworten über komplexe Quellen verwendet werden.

### 7.3 Langdock OpenAI Embeddings

Embeddings werden nicht mit Sonnet oder Haiku erzeugt.

Für semantische Suche verwenden wir die Langdock OpenAI Embedding API.

Langdock stellt dafür einen OpenAI-kompatiblen Embedding-Endpunkt bereit:

```text
POST https://api.langdock.com/openai/{region}/v1/embeddings
```

Für Deutschland/EU verwenden wir:

```text
POST https://api.langdock.com/openai/eu/v1/embeddings
```

Standardmodell:

```text
text-embedding-ada-002
```

Standardkonfiguration:

```env
EMBEDDING_PROVIDER=langdock
EMBEDDING_BASE_URL=https://api.langdock.com/openai/eu/v1
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536
EMBEDDING_ENCODING_FORMAT=float
```

Verwendung:

```text
Dokument-Chunks
  -> Langdock Embedding API
  -> Vektoren
  -> Qdrant

Nutzerfrage
  -> Langdock Embedding API
  -> Query-Vektor
  -> Qdrant Similarity Search
```

### 7.4 Reranking

Für den MVP verwenden wir zunächst Qdrant Scores und einfache Heuristiken.

Später kann Haiku als LLM-Reranker über Langdock genutzt werden.

MVP:

```text
Qdrant Top 30
  -> Score/Metadata-Heuristik
  -> Top 8 bis 12
  -> Sonnet 5
```

Produktversion:

```text
Qdrant Top 30 bis 50
  -> Haiku Reranking über Langdock
  -> Top 8 bis 15
  -> Sonnet 5
```

---

## 8. Modellrouting

```text
final_answer
  -> Sonnet 5

complex_summary
  -> Sonnet 5

source_comparison
  -> Sonnet 5

contradiction_check
  -> Sonnet 5

legal_reasoning
  -> Sonnet 5

technical_reasoning
  -> Sonnet 5

briefing
  -> Sonnet 5

intent_detection
  -> Haiku

query_rewrite
  -> Haiku

title_generation
  -> Haiku

followup_questions
  -> Haiku

simple_summary
  -> Haiku

classification
  -> Haiku

document_embedding
  -> Langdock OpenAI Embeddings

query_embedding
  -> Langdock OpenAI Embeddings

reranking_mvp
  -> Qdrant Score + Heuristik

reranking_advanced
  -> Haiku über Langdock
```

---

## 9. Komponenten

### 9.1 Frontend

Empfehlung:

```text
Next.js
React
Tailwind CSS
shadcn/ui 
```

Aufgaben:

- Login
- Notebook-Übersicht
- Notebook-Detailseite
- Quellenverwaltung
- Upload UI
- Chat UI
- Quellenkarten
- Notizen
- Studio-Panel
- Jobstatus anzeigen
- Fehleranzeigen
- Admin UI, optional

### 9.2 Backend API

Empfehlung:

```text
FastAPI oder NestJS
```

FastAPI ist besonders sinnvoll

Aufgaben:

- Authentifizierung
- User-/Notebook-Rechte
- Upload-Endpunkte
- Source-Status
- Chat-Endpunkt
- Retrieval-Orchestrierung
- Langdock-Client
- Embedding-Client
- Notizen
- Studio-Funktionen
- Admin-Endpunkte
- Audit-Logging
- Rate-Limiting

### 9.3 Worker

Empfehlung:

```text
Python Worker
Celery / RQ / Dramatiq
Redis als Broker
```

Aufgaben:

- Dokumente verarbeiten
- OCR durchführen
- Text extrahieren
- Tabellen extrahieren
- Chunks erzeugen
- Embeddings über Langdock generieren
- Qdrant indexieren
- Source Summaries generieren
- Batch-Jobs ausführen
- Fehler sauber protokollieren

### 9.4 PostgreSQL

PostgreSQL ist die primäre relationale Datenbank und Source of Truth.

Speichert:

- User
- Rollen
- Notebooks
- Quellen
- Chunks
- Nachrichten
- Notizen
- Jobs
- Audit Events
- Prompt-/Request-Metadaten ohne vertrauliche Vollinhalte
- Kosten-/Tokenmetriken

### 9.5 Qdrant

Qdrant ist die self-hosted Vector Database.

Speichert:

- Embeddings
- Chunk-Metadaten
- Notebook-ID
- Source-ID
- Page-Range
- Heading
- Chunk-Type
- Security Scope

Qdrant ist nicht die primäre Datenbank. PostgreSQL bleibt führend.

### 9.6 MinIO

MinIO speichert Dateien und Artefakte.

Speichert:

- Originaldateien
- extrahierter Text
- extrahierte Tabellen
- OCR-Ausgaben
- Seitenbilder, falls benötigt
- Preview-Dateien
- temporäre Exportdateien

### 9.7 Redis

Redis wird genutzt für:

- Queue
- Jobstatus
- Caching
- Rate Limit Counter
- kurzlebige Sessions, falls erforderlich

### 9.8 Caddy

Caddy übernimmt:

- Reverse Proxy
- HTTPS
- automatische Zertifikate
- Routing
- Security Headers
- optional Basic Auth für interne Admin-Oberflächen

---

## 10. Docker Compose

```yaml
services:
  caddy:
    image: caddy:2
    container_name: notebook-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - api

  frontend:
    build:
      context: ./apps/frontend
    container_name: notebook-frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    depends_on:
      - api

  api:
    build:
      context: ./apps/api
    container_name: notebook-api
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio

  worker:
    build:
      context: ./apps/worker
    container_name: notebook-worker
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio

  postgres:
    image: postgres:16
    container_name: notebook-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: notebook-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    container_name: notebook-qdrant
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage

  minio:
    image: minio/minio:latest
    container_name: notebook-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data

volumes:
  caddy_data:
  caddy_config:
  postgres_data:
  redis_data:
  qdrant_data:
  minio_data:
```

---

## 11. Caddyfile

Variante mit separater API-Subdomain:

```caddyfile
notebook.example.de {
    reverse_proxy frontend:3000
}

notebook-api.example.de {
    reverse_proxy api:8000
}
```

Variante mit einer Domain:

```caddyfile
notebook.example.de {
    reverse_proxy /api/* api:8000
    reverse_proxy frontend:3000
}
```

---

## 12. Repository-Struktur

```text
notebook-clone/
├── apps/
│   ├── frontend/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── package.json
│   │
│   ├── api/
│   │   ├── app/
│   │   │   ├── auth/
│   │   │   ├── notebooks/
│   │   │   ├── sources/
│   │   │   ├── chat/
│   │   │   ├── rag/
│   │   │   ├── langdock/
│   │   │   └── studio/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── worker/
│       ├── app/
│       │   ├── jobs/
│       │   ├── parsing/
│       │   ├── chunking/
│       │   ├── embeddings/
│       │   ├── indexing/
│       │   └── summaries/
│       ├── Dockerfile
│       └── pyproject.toml
│
├── packages/
│   ├── shared-types/
│   ├── prompts/
│   └── evals/
│
├── infra/
│   ├── caddy/
│   │   └── Caddyfile
│   ├── docker-compose.yml
│   ├── backup/
│   └── scripts/
│
├── docs/
│   ├── architecture.md
│   ├── rag-pipeline.md
│   ├── deployment.md
│   ├── langdock.md
│   └── security.md
│
├── .env.example
├── README.md
└── Makefile
```

---

## 13. Datenmodell

### 13.1 users

```text
id
email
name
role
created_at
updated_at
```

### 13.2 notebooks

```text
id
owner_id
title
description
visibility
created_at
updated_at
```

### 13.3 notebook_members

```text
id
notebook_id
user_id
role: owner | editor | viewer
created_at
```

### 13.4 sources

```text
id
notebook_id
uploaded_by
filename
original_filename
mime_type
storage_path
status: uploaded | processing | indexed | failed | deleted
page_count
token_count
checksum
error_message
created_at
updated_at
```

### 13.5 chunks

```text
id
notebook_id
source_id
chunk_index
chunk_type: text | table | image_caption | transcript | slide
page_start
page_end
heading
text
metadata_json
qdrant_point_id
created_at
```

### 13.6 messages

```text
id
notebook_id
user_id
role: user | assistant | system
content
model
citations_json
token_usage_json
created_at
```

### 13.7 notes

```text
id
notebook_id
created_by
title
content
source_refs_json
created_at
updated_at
```

### 13.8 jobs

```text
id
type
status: queued | running | completed | failed
source_id
notebook_id
payload_json
error_message
created_at
started_at
completed_at
```

### 13.9 audit_events

```text
id
user_id
event_type
entity_type
entity_id
metadata_json
created_at
```

### 13.10 langdock_requests

```text
id
user_id
notebook_id
job_id
request_type: completion | embedding | agent | usage_export
model
status_code
latency_ms
input_tokens
output_tokens
total_tokens
error_message
created_at
```

---

## 14. Dokumentenverarbeitung

### 14.1 Unterstützte Dateitypen im MVP

```text
PDF
DOCX
TXT
Markdown
HTML
CSV
XLSX
```

### 14.2 Später

```text
PowerPoint
Audio
Video
YouTube
Webseiten-Crawler
E-Mail-Threads
Bilder mit OCR
Scans
```

### 14.3 Pipeline

```text
Upload
  |
  v
Datei in MinIO speichern
  |
  v
Source in PostgreSQL anlegen
  |
  v
Job in Redis Queue legen
  |
  v
Worker verarbeitet Dokument
  |
  v
Text, Tabellen, Seitenstruktur extrahieren
  |
  v
Chunks erzeugen
  |
  v
Embeddings über Langdock erzeugen
  |
  v
Chunks in PostgreSQL speichern
  |
  v
Vektoren in Qdrant speichern
  |
  v
Source Status = indexed
```

### 14.4 Parsing

Empfehlung:

```text
Docling als primärer Parser
Unstructured als Fallback
Tesseract/PaddleOCR für OCR
python-docx für einfache DOCX-Fälle
pandas/openpyxl für CSV/XLSX
```

### 14.5 Chunking-Strategie

Kein blindes Fixed-Length-Chunking.

Besser:

```text
Dokument
  -> Seiten
  -> Überschriften
  -> Abschnitte
  -> Absätze
  -> Tabellen
  -> semantische Chunks
```

Empfohlene Chunkgrößen:

```text
Fließtext:
600 bis 1.200 Tokens

Overlap:
100 bis 150 Tokens

Verträge/Gutachten:
Abschnittsbasiert mit Seitenbezug

Tabellen:
Als eigene Chunks im Markdown-Format

Präsentationen:
Slide-basiert

Audio/Transkript:
Zeitabschnittsbasiert
```

---

## 15. Qdrant Collection

Da `text-embedding-ada-002` Vektoren mit 1536 Dimensionen erzeugt, muss die Qdrant Collection entsprechend angelegt werden.

```text
Collection:
notebook_chunks

Vector size:
1536

Distance:
Cosine
```

Payload pro Punkt:

```json
{
  "notebook_id": "nb_123",
  "source_id": "src_123",
  "chunk_id": "chk_123",
  "document_name": "Gutachten.pdf",
  "page_start": 12,
  "page_end": 13,
  "heading": "Schadensbild",
  "chunk_type": "text",
  "created_at": "2026-07-05T12:00:00Z"
}
```

---

## 16. RAG-Pipeline

### 16.1 Ablauf bei Nutzerfrage

```text
User Question
  |
  v
Intent Detection mit Haiku über Langdock
  |
  v
Query Rewriting mit Haiku über Langdock
  |
  v
Query Embedding über Langdock OpenAI Embeddings
  |
  v
Similarity Search in Qdrant
  |
  v
Optional: Haiku Reranking über Langdock
  |
  v
Context Assembly
  |
  v
Antwortgenerierung mit Sonnet 5 über Langdock
  |
  v
Citation Validation self-hosted
  |
  v
Antwort + Quellenkarten an Frontend
```

### 16.2 Query Understanding

Haiku erkennt:

```text
- normale Frage
- Zusammenfassung
- Vergleich
- Timeline
- FAQ
- konkrete Zahl
- Entscheidungsvorlage
- Widerspruchsanalyse
- Quellenfrage
- Suche nach bestimmtem Abschnitt
```

### 16.3 Retrieval

Empfohlen:

```text
Dense Vector Search
+ Metadata Filter
+ Notebook Scope
+ Source Scope
+ optional Keyword Pre-Filter
```

Filter:

```text
notebook_id = current_notebook
user_has_access = true
source_status = indexed
```

### 16.4 Context Assembly

Jeder Chunk wird mit klarer Quellenstruktur an das Modell übergeben:

```text
[Quelle 1]
source_id: src_123
chunk_id: chk_123
document_name: Gutachten.pdf
page_start: 12
page_end: 13
heading: Schadensbild
text:
...
```

### 16.5 Antwortgenerierung

Sonnet 5 erhält:

```text
System Prompt
Developer Prompt
User Question
Retrieved Context
Output Schema
```

### 16.6 Citation Validation

Nach der Modellantwort prüft das Backend:

```text
- Sind alle angegebenen source_ids bekannt?
- Gehören die Quellen zum Notebook?
- Hat der Nutzer Zugriff auf diese Quellen?
- Existieren Seitenzahlen?
- Wurden Quellen erfunden?
- Gibt es Aussagen ohne Quellen?
```

Optional kann ein zweiter Validator-Call mit Haiku oder Sonnet 5 über Langdock laufen.

---

## 17. Langdock Integration

### 17.1 Grundprinzip

Alle AI-Aufrufe gehen über einen eigenen Langdock Client.

```text
LangdockClient
  -> generate_sonnet()
  -> generate_haiku()
  -> embed()
  -> structured_output()
  -> stream()
  -> usage_export()
```

### 17.2 Environment

```env
# App
APP_ENV=production
APP_URL=https://notebook.example.de
API_URL=https://notebook.example.de/api

# Langdock
LANGDOCK_API_KEY=...
LANGDOCK_REGION=eu

# Claude via Langdock
LANGDOCK_ANTHROPIC_BASE_URL=https://api.langdock.com/anthropic/eu
LANGDOCK_PRIMARY_MODEL=<sonnet-5-id-aus-langdock>
LANGDOCK_FAST_MODEL=<haiku-id-aus-langdock>

# Embeddings via Langdock
EMBEDDING_PROVIDER=langdock
EMBEDDING_BASE_URL=https://api.langdock.com/openai/eu/v1
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536
EMBEDDING_ENCODING_FORMAT=float

# Optional Langdock Agent API
LANGDOCK_AGENT_BASE_URL=https://api.langdock.com/agent/v1
LANGDOCK_USE_AGENTS_FOR_STRUCTURED_TASKS=false

# Optional Langdock Knowledge API
LANGDOCK_KNOWLEDGE_API_ENABLED=false
LANGDOCK_KNOWLEDGE_BASE_URL=https://api.langdock.com/knowledge

# Reranking
RERANKER_PROVIDER=langdock_haiku
RERANKER_MODEL=${LANGDOCK_FAST_MODEL}
RERANKER_ENABLED=false

# Self-hosted Services
POSTGRES_HOST=postgres
POSTGRES_DB=notebook
POSTGRES_USER=notebook
POSTGRES_PASSWORD=...

REDIS_URL=redis://redis:6379/0

QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=notebook_chunks
QDRANT_VECTOR_SIZE=1536

MINIO_ENDPOINT=http://minio:9000
MINIO_BUCKET=notebook-files
MINIO_ROOT_USER=...
MINIO_ROOT_PASSWORD=...
```

### 17.3 Model Discovery

Modell-IDs werden nicht geraten und nicht im Code hart verdrahtet.

Sie werden über Langdock geprüft und anschließend in `.env` hinterlegt.

```bash
curl --request GET \
  --url https://api.langdock.com/agent/v1/models \
  --header "Authorization: Bearer <LANGDOCK_API_KEY>"
```

### 17.4 Langdock Embedding API Beispiel

```bash
curl --request POST \
  --url https://api.langdock.com/openai/eu/v1/embeddings \
  --header "Authorization: Bearer <LANGDOCK_API_KEY>" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "text-embedding-ada-002",
    "input": "Beispieltext für semantische Suche",
    "encoding_format": "float"
  }'
```

### 17.5 Python mit OpenAI-kompatiblem Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.langdock.com/openai/eu/v1",
    api_key="LANGDOCK_API_KEY"
)

response = client.embeddings.create(
    model="text-embedding-ada-002",
    input="Beispieltext für semantische Suche",
    encoding_format="float"
)

embedding = response.data[0].embedding
```

---

## 18. Prompt-Konzept

### 18.1 System Prompt für finale Antworten

```text
Du bist ein quellengebundener Research-Assistent.

Beantworte die Nutzerfrage ausschließlich auf Basis der bereitgestellten Quellen.
Nutze keine externen Informationen.
Erfinde keine Fakten, Seitenzahlen, Dokumentnamen oder Quellen.
Wenn die Quellen keine ausreichende Antwort enthalten, sage das klar.

Jede wesentliche Aussage muss mit einer Quelle belegt werden.
Wenn Quellen widersprüchlich sind, benenne den Widerspruch.
Wenn die Datenlage unklar ist, kennzeichne das als unklar.

Antworte präzise, strukturiert und sachlich.
```

### 18.2 Output-Schema

```json
{
  "answer": "string",
  "citations": [
    {
      "source_id": "string",
      "chunk_id": "string",
      "document_name": "string",
      "page_start": 1,
      "page_end": 1,
      "quote": "string",
      "supports_claim": "string"
    }
  ],
  "confidence": "low | medium | high",
  "missing_information": [
    "string"
  ],
  "follow_up_questions": [
    "string"
  ]
}
```

### 18.3 Haiku Prompt für Intent Detection

```text
Klassifiziere die Nutzeranfrage in genau eine Kategorie:

- question
- summary
- comparison
- timeline
- faq
- briefing
- extraction
- contradiction_check
- source_lookup
- unknown

Gib nur JSON zurück.
```

### 18.4 Haiku Prompt für Query Rewrite

```text
Formuliere die Nutzerfrage für eine semantische Suche über Dokument-Chunks um.
Erhalte Eigennamen, Fachbegriffe, Datumsangaben und Zahlen.
Erzeuge maximal 3 Suchvarianten.
Gib nur JSON zurück.
```

### 18.5 Haiku Prompt für Reranking

```text
Bewerte die Relevanz jedes Chunks für die Nutzerfrage auf einer Skala von 0 bis 5.

Gib ausschließlich JSON zurück.

Nutzerfrage:
{{question}}

Chunks:
{{chunks}}

Output:
{
  "ranked_chunks": [
    {
      "chunk_id": "string",
      "score": 0,
      "reason": "string"
    }
  ]
}
```

---

## 19. Studio-Funktionen

Das Studio erzeugt den NotebookLM-Charakter.

### 19.1 MVP-Studio

```text
- Quellenzusammenfassung
- Notebook-Zusammenfassung
- FAQ
- Timeline
- Briefing-Dokument
- wichtigste Zitate
- offene Fragen
```

### 19.2 Später

```text
- Audio Overview
- Podcast-Skript
- Lernkarten
- Glossar
- Quellenvergleich
- Argumentationsmatrix
- Risikoanalyse
- Maßnahmenplan
- Executive Summary
```

### 19.3 Modellwahl Studio

```text
Kurze Source Summary:
Haiku

Lange Notebook Summary:
Sonnet 5

FAQ:
Haiku für Entwurf, Sonnet 5 für finale hochwertige Version

Timeline:
Sonnet 5, wenn mehrere Quellen und Datumslogik

Podcast-Skript:
Sonnet 5

Follow-up Questions:
Haiku

Glossar:
Haiku

Widersprüche:
Sonnet 5
```

---

## 20. UI-Konzept

### 20.1 Layout

```text
Linke Spalte:
- Notebooks
- Quellen
- Notizen

Mitte:
- Chat
- Antwort
- Quellenverweise
- Follow-up-Fragen

Rechte Spalte:
- Studio
- Zusammenfassung
- FAQ
- Timeline
- Briefing
- Zitate
```

### 20.2 Quellenkarten

Jede Antwort zeigt Quellenkarten:

```text
Quelle 1
Dokument: Gutachten.pdf
Seite: 12
Abschnitt: Schadensbild
Zitat: "..."
```

### 20.3 Upload UX

```text
- Drag & Drop
- Dateiliste
- Status: hochgeladen, wird verarbeitet, indexiert, fehlgeschlagen
- Fehlerdetails
- Retry-Button
```

### 20.4 Chat UX

```text
- Fragefeld
- Quellenfilter
- Antwortstreaming
- Quellenchips
- „In Notiz übernehmen“
- „Als Briefing speichern“
- „Weitere Fragen“
```

---

## 21. Authentifizierung und Rechte

### 21.1 MVP

```text
- E-Mail/Login
- Demo-User
- Notebook Owner
- Private Notebooks
```

### 21.2 Später

```text
- Microsoft Entra ID
- SSO
- Rollen
- Team Workspaces
- Notebook Sharing
```

### 21.3 Rollenmodell

```text
Admin:
- alles verwalten

Owner:
- Notebook verwalten
- Quellen löschen
- Mitglieder einladen

Editor:
- Quellen hinzufügen
- Chatten
- Notizen bearbeiten

Viewer:
- lesen
- chatten, optional
```

---

## 22. Sicherheit

### 22.1 Mindestanforderungen

```text
- HTTPS über Caddy
- Secrets nur über .env oder Secret Store
- keine Dokumentinhalte in Logs
- Zugriff auf Quellen nur nach Berechtigungsprüfung
- MinIO Buckets nicht öffentlich
- signierte Download-URLs
- Rate Limits
- Upload Limits
- Dateitypprüfung
- Malware-Scan optional
- Löschkonzept
```

### 22.2 Kein Langdock-Key im Frontend

Der Langdock API Key darf niemals im Browser landen.

Nicht erlaubt:

```env
NEXT_PUBLIC_LANGDOCK_API_KEY=...
```

Erlaubt:

```text
Frontend
  -> Backend
  -> Langdock
```

### 22.3 Löschung

Beim Löschen einer Quelle müssen alle Artefakte entfernt werden:

```text
- PostgreSQL source record markieren oder löschen
- chunks löschen
- Qdrant points löschen
- MinIO original file löschen
- parsed artifacts löschen
- summaries löschen
```

### 22.4 Logging

Nicht loggen:

```text
- vollständige Dokumentinhalte
- vollständige Prompts mit vertraulichen Quellen
- API Keys
- personenbezogene Inhalte
```

Loggen:

```text
- Jobstatus
- Fehlercodes
- Tokenverbrauch
- Modellname
- Latenz
- Kostenabschätzung
- Nutzer-ID
- Notebook-ID
```

---

## 23. Rate Limits und Kostenkontrolle

Langdock-Limits wirken auf Workspace-Ebene.

Daher brauchen wir:

```text
- Worker Queue
- kontrollierte Parallelität
- Retry mit Exponential Backoff
- 429 Handling
- Token Budget pro Job
- Token Budget pro User
- Token Budget pro Notebook
- Caching von Summaries
- Caching von Embeddings
- Deduplizierung per Checksum
```

Embedding-Jobs dürfen nicht unkontrolliert parallel laufen.

Empfohlene erste Worker-Konfiguration:

```text
Embedding Worker Concurrency:
2 bis 4

Chat Completion Concurrency:
abhängig vom Langdock-Limit, initial konservativ

Retry:
429 -> Backoff 5s, 15s, 30s, 60s
```

---

## 24. Monitoring

Empfohlen:

```text
- Docker Logs
- Healthchecks
- Prometheus optional
- Grafana optional
- Sentry für Frontend/API Fehler
- Uptime Kuma für Verfügbarkeit
```

Zu messen:

```text
- Uploads pro Tag
- Verarbeitungsdauer pro Dokument
- Fehlgeschlagene Jobs
- durchschnittliche Chat-Latenz
- Tokenverbrauch je Modell
- Kosten je Notebook/User
- Qdrant Query Time
- Langdock API Errors
- Rate Limits
- Embedding Calls
```

---

## 25. Backup-Konzept

Zu sichern:

```text
PostgreSQL:
- tägliches Dump

MinIO:
- Object Storage Backup

Qdrant:
- Snapshots

.env:
- separat sicher verwahren

Caddy:
- Caddyfile
- Zertifikatsdaten optional, können meist neu erzeugt werden
```

Empfohlene Backup-Frequenz:

```text
PostgreSQL:
täglich

MinIO:
täglich oder inkrementell

Qdrant:
täglich

Retention:
7 tägliche Backups
4 wöchentliche Backups
3 monatliche Backups
```

---

## 26. API-Endpunkte

### 26.1 Auth

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

### 26.2 Notebooks

```text
GET    /api/notebooks
POST   /api/notebooks
GET    /api/notebooks/{id}
PATCH  /api/notebooks/{id}
DELETE /api/notebooks/{id}
```

### 26.3 Sources

```text
GET    /api/notebooks/{id}/sources
POST   /api/notebooks/{id}/sources/upload
GET    /api/sources/{source_id}
DELETE /api/sources/{source_id}
POST   /api/sources/{source_id}/reprocess
```

### 26.4 Chat

```text
GET  /api/notebooks/{id}/messages
POST /api/notebooks/{id}/chat
```

### 26.5 Studio

```text
POST /api/notebooks/{id}/studio/summary
POST /api/notebooks/{id}/studio/faq
POST /api/notebooks/{id}/studio/timeline
POST /api/notebooks/{id}/studio/briefing
POST /api/notebooks/{id}/studio/audio-script
```

### 26.6 Notes

```text
GET    /api/notebooks/{id}/notes
POST   /api/notebooks/{id}/notes
PATCH  /api/notes/{note_id}
DELETE /api/notes/{note_id}
```

---

## 27. MVP-Scope

### 27.1 MVP 1: Kernsystem

```text
- Docker Compose Stack
- Caddy HTTPS
- Frontend
- Backend
- Worker
- PostgreSQL
- Redis
- Qdrant
- MinIO
- Login/Demo-User
- Notebook erstellen
- PDF/DOCX/TXT/MD Upload
- Parsing
- Chunking
- Langdock Embeddings
- Qdrant Indexierung
- Chat über Quellen
- Antwort mit Quellenangaben
```

### 27.2 MVP 2: NotebookLM-Feeling

```text
- Source Summary
- Notebook Summary
- FAQ
- Timeline
- Briefing
- Quellenkarten
- Follow-up-Fragen
- Notizen
- Antwort in Notiz übernehmen
```

### 27.3 MVP 3: Produktreife

```text
- Team Workspaces
- Sharing
- Microsoft Entra ID
- Admin Dashboard
- Kostenmonitoring
- Audio Overview
- Transkription
- Webseitenimport
- PowerPoint-Support
- Evaluation Suite
```

---

## 28. Roadmap

### Woche 1: Fundament

```text
- Repo anlegen
- Docker Compose
- Caddy
- PostgreSQL
- Redis
- Qdrant
- MinIO
- Backend Skeleton
- Frontend Skeleton
- .env.example
```

### Woche 2: Upload und Processing

```text
- Upload API
- MinIO Integration
- Source Tabelle
- Worker Queue
- PDF/DOCX/TXT Parser
- Chunking
- Langdock Embeddings
- Qdrant Indexing
```

### Woche 3: Chat und RAG

```text
- Chat UI
- Langdock Haiku Intent Detection
- Langdock Haiku Query Rewrite
- Retrieval
- optional Reranking
- Langdock Sonnet 5 Answer Generation
- Quellenkarten
- Citation Validation
```

### Woche 4: Studio und Demo

```text
- Summary
- FAQ
- Timeline
- Briefing
- Notizen
- Demo Notebook
- README
- Architekturdiagramm
- Loom Video oder Agent Session
```

---

## 29. Beispiel: RAG Request Flow

```text
POST /api/notebooks/{id}/chat

Request:
{
  "message": "Was sind die wichtigsten Risiken in diesen Unterlagen?",
  "source_ids": ["optional"],
  "mode": "grounded"
}
```

Backend:

```text
1. Rechte prüfen
2. Message speichern
3. Intent mit Haiku über Langdock erkennen
4. Query mit Haiku über Langdock umschreiben
5. Query Embedding über Langdock erzeugen
6. Qdrant Retrieval
7. Optional Haiku Reranking über Langdock
8. Prompt bauen
9. Langdock Sonnet 5 aufrufen
10. JSON Antwort validieren
11. Assistant Message speichern
12. Antwort an Frontend geben
```

Response:

```json
{
  "answer": "Die wichtigsten Risiken sind ...",
  "citations": [
    {
      "source_id": "src_123",
      "chunk_id": "chk_123",
      "document_name": "Gutachten.pdf",
      "page_start": 4,
      "page_end": 5,
      "quote": "..."
    }
  ],
  "confidence": "high",
  "follow_up_questions": [
    "Welche Maßnahmen werden empfohlen?",
    "Welche Kostenpositionen sind belegt?"
  ]
}
```

---

## 30. Beispiel: Modell-Router

```python
class ModelRouter:
    def select_model(self, task: str, risk: str = "normal") -> str:
        sonnet_tasks = {
            "final_answer",
            "complex_summary",
            "source_comparison",
            "contradiction_check",
            "legal_reasoning",
            "technical_reasoning",
            "briefing",
        }

        haiku_tasks = {
            "intent_detection",
            "query_rewrite",
            "title_generation",
            "followup_questions",
            "simple_summary",
            "classification",
            "reranking",
        }

        embedding_tasks = {
            "document_embedding",
            "query_embedding",
        }

        if task in embedding_tasks:
            return "langdock_embedding"

        if task in sonnet_tasks:
            return "sonnet"

        if task in haiku_tasks:
            return "haiku"

        if risk == "high":
            return "sonnet"

        return "haiku"
```

---

## 31. Risiken und Gegenmaßnahmen

### 31.1 Halluzinationen

Risiko:

```text
Modell erfindet Aussagen oder Quellen.
```

Gegenmaßnahmen:

```text
- strikter System Prompt
- Quellenkontext begrenzen
- JSON Output
- Citation Validation
- Antwort nur mit bekannten source_ids akzeptieren
- Abstention erlauben
```

### 31.2 Rate Limits

Risiko:

```text
Zu viele oder zu große Langdock-Anfragen.
```

Gegenmaßnahmen:

```text
- eigene Retrieval-Schicht
- kleine Prompts
- Haiku für Nebenaufgaben
- Caching
- Queue für Batch-Jobs
- Tokenmonitoring
```

### 31.3 Schlechte Antworten durch schlechtes Parsing

Risiko:

```text
PDFs werden unvollständig oder falsch extrahiert.
```

Gegenmaßnahmen:

```text
- Docling/Unstructured
- OCR-Fallback
- Tabellen separat extrahieren
- Parsing-Artefakte speichern
- Preview/Debug-Ansicht
```

### 31.4 Schlechte Suche

Risiko:

```text
Retrieval findet falsche Chunks.
```

Gegenmaßnahmen:

```text
- gute Chunking-Strategie
- Query Rewrite mit Haiku
- Qdrant Metadata Filter
- optional Haiku Reranking
- Evaluation Set
```

### 31.5 Kostenkontrolle

Risiko:

```text
Sonnet 5 wird für zu viele kleine Aufgaben genutzt.
```

Gegenmaßnahmen:

```text
- Modell-Router
- Haiku für Nebenaufgaben
- Caching von Summaries
- Batch-Jobs
- Token Budgets pro User/Notebook
```

---

## 32. Evaluation

Für Qualität brauchen wir ein kleines Testset.

### 32.1 Testfälle

```text
- einfache Faktfrage
- Frage mit Seitenbezug
- Frage über mehrere Dokumente
- Widerspruch zwischen Quellen
- nicht beantwortbare Frage
- Zusammenfassung
- Timeline
- Tabellenfrage
- juristische/technische Analyse
```

### 32.2 Metriken

```text
- Antwort korrekt
- Antwort vollständig
- Quellen korrekt
- keine erfundenen Quellen
- relevante Chunks gefunden
- Latenz
- Tokenverbrauch
- Kosten
```

### 32.3 Golden Dataset

```text
docs/evals/
├── sample_sources/
├── questions.json
├── expected_answers.json
└── evaluation_results.json
```

---

## 33. Klare Projektbeschreibung

```text
The application is fully self-hosted and runs on a Linux server using Docker Compose, Caddy, PostgreSQL, Redis, MinIO and Qdrant.

All AI model access is centralized through Langdock. The system does not call OpenAI, Anthropic or other model providers directly.

Langdock is used for:
- Claude Sonnet 5 as the primary reasoning and answer generation model
- Claude Haiku for low-latency utility tasks
- Langdock OpenAI Embeddings for semantic search
- optional Agents API for structured tasks
- optional Usage Export for cost monitoring

The RAG pipeline itself is controlled by the application:
documents are parsed, chunked, embedded, indexed and retrieved by the self-hosted backend and worker services. Only the selected relevant context is sent to Langdock for generation.
```

---

## 34. Nächster konkreter Meilenstein

Der erste technische Meilenstein ist:

```text
PDF hochladen
  -> Datei in MinIO speichern
  -> Text extrahieren
  -> Chunks erzeugen
  -> Embeddings über Langdock erzeugen
  -> Vektoren in Qdrant speichern
  -> Frage stellen
  -> relevante Chunks finden
  -> Antwort mit Sonnet 5 über Langdock generieren
  -> Quellenkarten anzeigen
```

Wenn dieser Flow stabil läuft, ist die fachliche Basis des Systems belastbar.

Alles Weitere baut darauf auf.
