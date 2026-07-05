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

## Deployment mit geteiltem Caddy (Multi-Projekt-Host)

Auf einem Host, auf dem Port 80/443 bereits von einem anderen, unabhängigen
Caddy-Container belegt sind (z. B. ein gemeinsam genutzter Caddy für mehrere
Projekte), kann NotebookLMC diesen bestehenden Caddy mitbenutzen, statt den
eigenen `caddy`-Service zu starten:

```bash
docker compose stop caddy   # eigener caddy-Service bleibt ungestartet
docker compose -f docker-compose.yml -f docker-compose.shared-caddy.yml \
  up -d --no-deps api frontend
```

`docker-compose.shared-caddy.yml` hängt `api` und `frontend` zusätzlich in
das externe Docker-Netzwerk des bereits laufenden, gemeinsamen Caddy
(`shared_caddy_net`, Default-Name `fremdes-projekt-a_caddy-network` - **muss** auf den
tatsächlichen Netzwerknamen des jeweiligen Hosts angepasst werden, siehe
Kommentar in der Datei). Im Caddyfile des gemeinsamen Caddy muss dafür
manuell ein zusätzlicher Site-Block ergänzt werden, der `/api/*` an `api:8000`
und alles andere an `frontend:3000` weiterleitet (Vorlage: `infra/caddy/Caddyfile`
in diesem Repo, Routing-Prinzip 1:1 übernehmen).

**Platzhalter-Domain ersetzen:** Solange keine echte Domain vorhanden ist,
kann im Site-Block des gemeinsamen Caddy vorübergehend eine Platzhalter-Domain
verwendet werden (z. B. `notebooklmc.example.com`). Da `example.com` von der
Let's-Encrypt-ACME-Policy für Zertifikate geblockt ist, muss ein solcher
Platzhalter-Block per `http://`-Präfix (`http://notebooklmc.example.com { ... }`)
explizit ohne automatisches HTTPS betrieben werden. Sobald die echte Domain
feststeht: DNS-A-Record (und ggf. AAAA) auf diesen Server zeigen lassen, den
`http://`-Präfix entfernen und den Site-Block auf die echte Domain ändern -
Caddy bezieht dann automatisch ein Let's-Encrypt-Zertifikat.

**Wichtiger Next.js-Fallstrick bei mehreren Netzwerken:** Der
Next.js-Standalone-Server (`apps/frontend/Dockerfile` → `server.js`) bindet
standardmäßig an die per Docker-DNS aufgelöste `HOSTNAME`-IP statt an
`0.0.0.0`. Sobald `frontend` (wie hier) in zwei Docker-Netzwerken hängt, kann
diese Auflösung auf die falsche Netzwerk-IP zeigen und der Server ist über
das andere Netzwerk nicht mehr erreichbar. `docker-compose.shared-caddy.yml`
setzt deshalb explizit `HOSTNAME=0.0.0.0` für `frontend`.

Der eigene `caddy`-Service in `docker-compose.yml` bleibt für Hosts erhalten,
auf denen Port 80/443 frei sind (Standardfall, z. B. ein dedizierter Server
nur für NotebookLMC) - dort einfach `docker compose up -d` ohne die
Zusatz-Datei verwenden.

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
