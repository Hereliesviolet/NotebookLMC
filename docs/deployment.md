# Deployment

## Lokal (Docker Compose)

```bash
cp .env.example .env
# .env bearbeiten: LANGDOCK_API_KEY, LANGDOCK_PRIMARY_MODEL, LANGDOCK_FAST_MODEL setzen
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Ports (lokale Entwicklung, zusätzlich zu Caddy auf 80/443):

| Service | Port |
| --- | --- |
| Frontend | 3000 |
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Qdrant | 6333 |
| MinIO (S3-API / Konsole) | 9000 / 9001 |

## Caddy / Reverse Proxy

`infra/caddy/Caddyfile` enthält standardmäßig eine lokale Variante ohne
echte Domain (`:80`), die `/api/*` an `api:8000` und alles andere an
`frontend:3000` weiterleitet. Für Produktion die Domain-Variante am Ende der
Datei aktivieren - Caddy übernimmt dann automatisch die HTTPS-Zertifikate
via ACME/Let's Encrypt. Es sind keine weiteren Anpassungen an Frontend/API
nötig, solange `/api` als Präfix erreichbar bleibt.

## Frontend-Build-Variable

`NEXT_PUBLIC_API_URL` wird von Next.js **zur Build-Zeit** in das JS-Bundle
eingebettet, nicht zur Laufzeit gelesen. Deshalb wird sie in
`docker-compose.yml` als `build.args` an den `frontend`-Service übergeben,
nicht als `environment:`. Nach einer Änderung von `NEXT_PUBLIC_API_URL` in
`.env` muss das Frontend-Image neu gebaut werden:

```bash
docker compose build frontend
docker compose up -d frontend
```

## Datenbank-Migrationen

Migrationen werden ausschließlich vom `api`-Service verwaltet (Alembic).
Der `worker` liest/schreibt dieselben Tabellen, führt aber nie DDL aus.

```bash
make migrate                          # Migrationen anwenden
make migrate-autogenerate msg="..."   # neue Migration aus Modell-Änderungen generieren
```

## Backups

Platzhalter-Skripte unter `infra/backup/`:

- `backup_postgres.sh` - `pg_dump` des `notebook`-Schemas
- `backup_minio.sh` - `mc mirror` des `notebook-files`-Buckets
- `backup_qdrant.sh` - Qdrant-Snapshot der `notebook_chunks`-Collection

Alle drei sind eigenständig ausführbar und schreiben nach
`infra/backup/output/` (siehe `.gitignore`).

## Skalierung / Betrieb

- **Worker-Concurrency:** mehrere `worker`-Container/Prozesse können
  parallel gestartet werden (RQ verteilt Jobs automatisch über alle
  Worker, die auf dieselben Queues hören). Für getrennte Concurrency von
  Embedding- vs. Default-Jobs zwei separate Worker-Deployments mit
  jeweils nur einer Queue betreiben.
- **Healthchecks:** `postgres`, `redis`, `qdrant`, `minio` haben
  Docker-Healthchecks; `api`/`worker` starten erst, wenn diese "healthy" sind.
- **Stateless API/Worker:** beide Services halten keinen lokalen State -
  horizontale Skalierung ist ohne Sticky-Sessions möglich (Dev-Auth-Token ist
  zustandslos, siehe `docs/security.md`).

## Troubleshooting

- **Port 80/443 bereits belegt:** Läuft auf dem Host bereits ein anderer
  Reverse Proxy (z. B. ein weiterer Caddy/Nginx-Container eines anderen
  Projekts), schlägt `docker compose up caddy` mit `port is already
  allocated` fehl. Entweder den anderen Dienst stoppen, oder für lokale
  Tests die Caddy-Ports in `docker-compose.yml` auf freie Ports mappen
  (z. B. `"8080:80"`) - `frontend` (3000) und `api` (8000) bleiben davon
  unberührt und sind währenddessen direkt erreichbar.

## Environment-Variablen

Vollständige Liste inkl. Kommentaren: [`.env.example`](../.env.example).
Kritisch vor dem ersten produktiven Start zu setzen:

- `LANGDOCK_API_KEY`, `LANGDOCK_PRIMARY_MODEL`, `LANGDOCK_FAST_MODEL`
- `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` (Default-Werte nur für lokale Entwicklung!)
- `APP_URL` / `NEXT_PUBLIC_API_URL` (echte Domain statt `localhost`)
