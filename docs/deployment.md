# Deployment

## Lokal (Docker Compose)

```bash
cp .env.example .env
# .env bearbeiten: LANGDOCK_API_KEY, LANGDOCK_PRIMARY_MODEL, LANGDOCK_FAST_MODEL setzen
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Ports (lokale Entwicklung, zusätzlich zu Caddy auf 80/443 sofern der eigene
`caddy`-Service läuft - auf Hosts mit geteiltem Caddy oder ohne Port-80-Zugriff
reicht Port 3000 allein, siehe nächster Abschnitt):

| Service | Port |
| --- | --- |
| Frontend | 3000 |
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Qdrant | 6333 |
| MinIO (S3-API / Konsole) | 9000 / 9001 |

## Direkter Zugriff ohne Caddy (manueller Next.js Route-Handler-Proxy)

Seit der Umstellung auf same-origin/relative API-Pfade (siehe Abschnitt
"Frontend-Build-Variable" unten) besitzt das Frontend einen catch-all
App-Router-Route-Handler unter `apps/frontend/app/api/[...path]/route.ts`,
der `/api/*` **server-seitig** (im Next.js-Server selbst, nicht im Browser)
per manuellem `fetch()` an `INTERNAL_API_URL` (Default `http://api:8000`)
weiterleitet - inklusive Query-Parametern, Body, Headers (insbesondere
`Authorization`) und Streaming der Response (auch für Binärantworten wie
PNG/PDF/DOCX-Exports).

**Historie:** Bis 2026-07 übernahm das dafür ein deklaratives
`rewrites()` in `next.config.mjs`. Dessen interner Node-`http`-Proxy hat
jedoch keine konfigurierbare Zeitgrenze und brach lang laufende
Studio-Generierungen (Briefing/Quiz/Mindmap, 30-60+s) nach einer festen,
zu kurzen Frist mit `socket hang up`/`ECONNRESET` ab, obwohl die API im
Hintergrund erfolgreich weiterlief - im Browser erschien das als
"API error 500" trotz gesunder API. Der manuelle Route-Handler ersetzt
`rewrites()` vollständig und steuert das Timeout explizit selbst (siehe
Konstante `PROXY_TIMEOUT_MS` in `route.ts`, aktuell 310s - passend zum
Gunicorn-`--timeout 300` in `apps/api/Dockerfile`, mit 10s Puffer, damit
Gunicorns eigener, saubererer Timeout-Fehler zuerst greift statt eines
Gleichstands mit dem Proxy-Timeout).

Das ermöglicht direkten Zugriff auf die App über Port 3000 (z. B. lokale
Entwicklung, Cursor-Portforwarding, oder jede Sandbox/jeder Host, auf dem
Port 80/443 aus anderen Gründen nicht verfügbar sind), ohne dass der eigene
`caddy`-Service dafür gestartet werden muss:

```bash
docker compose up -d --build frontend api   # caddy bleibt ungestartet
curl http://localhost:3000/                 # Frontend
curl http://localhost:3000/api/notebooks    # API ueber den Next.js-Route-Handler-Proxy
```

`INTERNAL_API_URL` ist im Gegensatz zu `NEXT_PUBLIC_API_URL` eine reine
**Server-Runtime-Env** (kein `NEXT_PUBLIC_*`-Build-Arg) - sie wird bei jedem
Start des Frontend-Containers neu aus der Umgebung gelesen, ein Image-Rebuild
nach einer Änderung ist also nicht nötig (ein `docker compose up -d frontend`
genügt). Der Default `http://api:8000` passt sowohl für den Standard-Betrieb
(`docker-compose.yml` allein) als auch für den Betrieb mit geteiltem Caddy
(`docker-compose.shared-caddy.yml`, siehe unten) unverändert, da `api` in
beiden Fällen im `default`-Netzwerk dieses Projekts erreichbar bleibt.

Dieser Mechanismus ersetzt Caddy NICHT für den produktiven Betrieb (Caddy
übernimmt weiterhin TLS-Terminierung, Security-Header, Logging etc.) - er
ist primär für lokale Entwicklung/Tests ohne Port-80-Zugriff gedacht.

## Caddy / Reverse Proxy

`infra/caddy/Caddyfile` enthält standardmäßig eine lokale Variante ohne
echte Domain (`:80`), die `/api/*` an `api:8000` und alles andere an
`frontend:3000` weiterleitet. Für Produktion die Domain-Variante am Ende der
Datei aktivieren - Caddy übernimmt dann automatisch die HTTPS-Zertifikate
via ACME/Let's Encrypt. Es sind keine weiteren Anpassungen an Frontend/API
nötig, solange `/api` als Präfix erreichbar bleibt.

## Deployment mit geteiltem Caddy (Multi-Projekt-Host)

**WICHTIG - ausschließlich diesen Weg verwenden, niemals parallel zum eigenen
`caddy`-Service:** Ist auf einem Host bereits ein unabhängiger, gemeinsam
genutzter Caddy-Container aktiv, der Port 80/443 dauerhaft belegt (konkret auf
diesem Server beobachtet: `fremdes-projekt-a-caddy-1` aus dem separaten Projekt `<pfad-zum-anderen-projekt>`,
`0.0.0.0:80->80`/`0.0.0.0:443->443`), kann der eigene `caddy`-Service in
`docker-compose.yml` dort **niemals** erfolgreich starten (Port-Konflikt) - er
bleibt sonst dauerhaft im Zustand `Created` hängen. Auf solchen Hosts gilt
daher ausnahmslos:

- Nur `docker-compose.shared-caddy.yml` als Overlay zusätzlich zu
  `docker-compose.yml` verwenden (Befehle unten).
- Den eigenen `caddy`-Service dauerhaft gestoppt UND entfernt lassen
  (`docker compose stop caddy && docker compose rm -f caddy`) - nicht nur
  einmalig stoppen, sondern sicherstellen, dass er nach einem künftigen
  `docker compose up -d` (ohne explizite Service-Liste) nicht versehentlich
  wieder mitgestartet wird. Am sichersten: immer mit expliziter Service-Liste
  wie in den Befehlen unten arbeiten, nie pauschal `docker compose up -d`
  ohne Service-Namen auf einem solchen Host.
- `docker compose ps -a` regelmäßig prüfen, um sicherzugehen, dass kein
  `caddy`-Container im Zustand `Created`/Fehler hängt.

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

**Konkretes Beispiel (produktiv umgesetzt):** `<produktions-domain>` läuft
über exakt diesen Weg auf einem Host, auf dem bereits ein gemeinsamer Caddy
(`fremdes-projekt-a-caddy-1`, Repo `<pfad-zum-anderen-projekt>`) für andere Projekte (fremdes-projekt-a, fremdes-projekt-b) aktiv
ist:

1. DNS-A-Record von `<produktions-domain>` auf die Server-IP gesetzt (per
   `dig @8.8.8.8 <produktions-domain> +short` und `dig @1.1.1.1 ...`
   gegen zwei unabhängige Resolver verifiziert, bevor der Site-Block
   aktiviert wurde - ohne korrektes DNS bricht die Let's-Encrypt-Challenge).
   **Sowohl A- als auch AAAA-Record prüfen:** Ein AAAA-Record, der (z. B.
   als Altlast eines anderen Hosting-Anbieters) auf eine falsche IPv6-Adresse
   zeigt, führt bei IPv6-bevorzugenden Clients zu einem TLS-Fehler
   (falsches Zertifikat des fremden Hosts), selbst wenn der A-Record korrekt
   ist und Caddy auf diesem Server ein gültiges Zertifikat besitzt - Fix:
   AAAA-Record entfernen oder auf die tatsächliche Server-IPv6-Adresse
   (`ip -6 addr show scope global`) korrigieren.
2. `git -C <pfad-zum-anderen-projekt> update-index --skip-worktree caddy_config/Caddyfile`
   ausgeführt, bevor die Datei bearbeitet wurde (siehe Warnhinweis oben).
3. Platzhalter-Block auf `<produktions-domain>` (ohne `http://`-Präfix)
   geändert, Security-Header (`Strict-Transport-Security`, `nosniff`,
   `DENY`, `Referrer-Policy`) und JSON-Access-Log analog zum
   `fremdes-projekt-b.example.de`-Block übernommen.
4. `docker exec fremdes-projekt-a-caddy-1 caddy validate --config /etc/caddy/Caddyfile`
   vor jedem Reload, danach `docker exec fremdes-projekt-a-caddy-1 caddy reload --config
   /etc/caddy/Caddyfile`.
5. Verifiziert per `curl -I https://<produktions-domain>/` (Frontend) und
   `curl -I https://<produktions-domain>/api/health` (API) sowie
   Regressionscheck der Nachbarprojekte (`fremdes-projekt-a.example.de`,
   `fremdes-projekt-b.example.de` weiterhin erreichbar).

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
`.env` muss das Frontend-Image neu gebaut werden (ein einfacher `restart`
reicht **nicht**, da die Variable bereits fest im JS-Bundle steht):

```bash
docker compose build frontend
docker compose up -d frontend
```

**Normalfall: leer lassen (same-origin über Caddy).** `NEXT_PUBLIC_API_URL`
sollte im Regelfall leer bleiben (`NEXT_PUBLIC_API_URL=` bzw. Variable in
`.env` weglassen). `apps/frontend/lib/api-client.ts` fällt dann auf einen
leeren String zurück, wodurch alle `fetch()`-Aufrufe zu relativen Pfaden wie
`/api/notebooks` statt absoluten URLs wie `http://localhost:8000/api/notebooks`
werden. Der Browser schickt diese Requests an denselben Origin, von dem die
Seite geladen wurde (egal ob `http://localhost`, eine echte Domain oder eine
Server-IP) - Caddy leitet `/api/*` serverseitig an `api:8000` weiter (siehe
`infra/caddy/Caddyfile`), der Browser selbst muss `api:8000` nie direkt
kennen oder erreichen können. Das behebt insbesondere das Problem, dass ein
Browser auf einem *anderen* Gerät als dem Server sonst versucht,
`localhost:8000` auf dem eigenen Endgerät zu erreichen ("Load failed"), statt
den Server zu kontaktieren.

**Sonderfall: absolute URL setzen.** Nur wenn die API bewusst auf einer
komplett getrennten Domain/Subdomain betrieben wird (z. B. Frontend auf
`notebook.example.de`, API auf `notebook-api.example.de`, siehe
Separate-Subdomain-Variante in `infra/caddy/Caddyfile`), muss
`NEXT_PUBLIC_API_URL` auf die volle API-URL gesetzt werden. In diesem Fall
greift beim Browser-Zugriff echtes Cross-Origin-CORS - stelle sicher, dass
`APP_URL` (siehe unten) auf die Frontend-Domain zeigt, damit
`allow_origins` in `apps/api/app/core/config.py`/`app/main.py` diese Anfragen
akzeptiert.

## `APP_URL` bei Domain-Wechseln anpassen

`APP_URL` (`.env`) wird von der API ausschließlich für CORS verwendet
(`allow_origins=[settings.app_url]` in `apps/api/app/main.py`) - relevant für
Szenarien mit direktem, nicht über Caddy same-origin geroutetem Zugriff auf
die API, z. B.:

- lokale Entwicklung ohne Docker/Caddy, bei der ein separat gestarteter
  Frontend-Dev-Server (z. B. `npm run dev` auf Port 3000) direkt gegen die
  API auf Port 8000 spricht (Cross-Origin);
- der oben beschriebene Sonderfall einer getrennten API-Subdomain.

Beim same-origin-Betrieb über Caddy (Normalfall, `NEXT_PUBLIC_API_URL` leer)
sieht der Browser Frontend und API dagegen als **einen** Origin - dafür ist
kein CORS nötig, `APP_URL` spielt für diesen Pfad keine Rolle.

**Wichtig:** Wird die öffentliche Domain/IP des Servers geändert (z. B. Umzug
von `localhost`/einer Test-IP auf eine echte Domain), muss `APP_URL` in `.env`
auf diese neue Domain/IP aktualisiert werden, sonst schlagen die oben
genannten direkten Cross-Origin-Zugriffe mit einem CORS-Fehler fehl. Für den
Caddy-same-origin-Pfad (der Regelfall für Endnutzer im Browser) ist das nicht
erforderlich, da dort kein CORS greift.

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
  horizontale Skalierung ist ohne Sticky-Sessions möglich, da Sessions in
  Redis (nicht im API-Prozess) gehalten werden, siehe `docs/security.md`.

## Troubleshooting

- **Port 80/443 bereits belegt:** Läuft auf dem Host bereits ein anderer
  Reverse Proxy (z. B. ein weiterer Caddy/Nginx-Container eines anderen
  Projekts), schlägt `docker compose up caddy` mit `port is already
  allocated` fehl. Entweder den anderen Dienst stoppen, oder für lokale
  Tests die Caddy-Ports in `docker-compose.yml` auf freie Ports mappen
  (z. B. `"8080:80"`) - `frontend` (3000) und `api` (8000) bleiben davon
  unberührt und sind währenddessen direkt erreichbar (siehe auch Abschnitt
  "Direkter Zugriff ohne Caddy" oben für den same-origin-Fall über die
  Next.js-Rewrites).
- **Eigener `caddy`-Container hängt dauerhaft im Zustand `Created`:** Typisches
  Symptom, wenn Port 80/443 durch einen bereits laufenden, unabhängigen
  Caddy-Container eines anderen Projekts dauerhaft belegt sind (siehe Abschnitt
  "Deployment mit geteiltem Caddy" oben) - der eigene `caddy`-Service kann in
  diesem Fall grundsätzlich nie erfolgreich starten. Fix: eigenen Service
  endgültig stoppen und entfernen (`docker compose stop caddy && docker
  compose rm -f caddy`) und stattdessen ausschließlich
  `docker-compose.shared-caddy.yml` für `api`/`frontend` verwenden.

## Environment-Variablen

Vollständige Liste inkl. Kommentaren: [`.env.example`](../.env.example).
Kritisch vor dem ersten produktiven Start zu setzen:

- `LANGDOCK_API_KEY`, `LANGDOCK_PRIMARY_MODEL`, `LANGDOCK_FAST_MODEL`
- `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` (Default-Werte nur für lokale Entwicklung!)
- `APP_URL` (echte Domain/IP statt `localhost`, siehe Abschnitt oben - nur für
  direkten, nicht-Caddy-proxied Zugriff auf die API relevant)
- `NEXT_PUBLIC_API_URL` (im Normalfall **leer lassen**, siehe Abschnitt
  "Frontend-Build-Variable" oben - nur im Sonderfall einer getrennten
  API-Domain/Subdomain setzen, dann Image neu bauen)
