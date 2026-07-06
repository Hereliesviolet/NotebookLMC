# Security

## Auth

Echte E-Mail/Passwort-Authentifizierung mit serverseitigen Sessions - kein
Dev-/Demo-Token mehr. Implementiert in `apps/api/app/core/security.py`
(Passwort-Hashing, `get_current_user`), `apps/api/app/core/sessions.py`
(Redis-Session-Store) und `apps/api/app/auth/router.py`
(`/register`, `/login`, `/logout`, `/me`).

**Passwörter:** Argon2 (`argon2-cffi`, `PasswordHasher`) - der aktuell
empfohlene Passwort-Hash-Algorithmus (Winner der Password Hashing
Competition), inklusive automatischem Salt pro Hash. Mindestlänge
`MIN_PASSWORD_LENGTH` (Default `10`, aus `.env`) statt erzwungener
Zeichenklassen-Komplexität, gemäß aktueller NIST-800-63B-Empfehlung.

**Sessions:** `POST /api/auth/login` legt bei Erfolg eine Server-Session in
Redis an (`session:<opaque-id>` → `user_id`, `SESSION_TTL_SECONDS`
Sliding-TTL - jede erfolgreiche Prüfung verlängert die TTL) und setzt zwei
Cookies:

- `session_id` - `httpOnly`, `Secure` (steuerbar über
  `SESSION_COOKIE_SECURE`, siehe unten), `SameSite=Lax`. Der Browser schickt
  dieses Cookie automatisch mit, JavaScript kann es nicht auslesen.
- `csrf_token` - **nicht** `httpOnly` (siehe CSRF-Abschnitt unten), sonst
  identische Attribute.

`get_current_user` liest ausschließlich `session_id` aus dem Cookie, schlägt
in Redis nach und lädt den zugehörigen User aus Postgres. `POST
/api/auth/logout` zerstört die Redis-Session und löscht beide Cookies.

**Rate-Limiting:** `apps/api/app/core/rate_limit.py` implementiert einen
einfachen Redis-Fixed-Window-Zähler (`login_attempts:<ip>:<email>`, `INCR` +
`EXPIRE 60`) - maximal 5 Login-Versuche pro Minute pro IP+E-Mail-Kombination,
danach `429` mit `Retry-After`-Header. Bewusst kein zusätzliches Paket
(z. B. `slowapi`), da nur dieser eine Zähler benötigt wird.

**Rollen/Sharing:** `notebook_members` (bereits im Datenmodell vorhanden) für
rollenbasierten Zugriff auf gemeinsame Notebooks ist weiterhin nur
vorbereitet, nicht aktiv genutzt - `notebooks/service.py::assert_can_access()`
prüft aktuell nur Besitzerschaft (`owner_id`).

**Lokale Entwicklung:** `make seed` legt einen Demo-User mit Passwort aus
`DEV_DEMO_USER_PASSWORD` (`.env`) an - es gibt keinen automatischen
Dev-Login mehr, auch lokal läuft jede Anmeldung über den echten
Login-Screen (`/login`).

## CSRF-Schutz

Da Auth jetzt über Cookies statt über einen `Authorization`-Header läuft,
ist CSRF ein reales Risiko (Cookies werden vom Browser automatisch bei
jedem Request an die Domain mitgeschickt, auch von fremden Seiten
ausgelöst) - `CsrfMiddleware` (`apps/api/app/core/middleware.py`)
implementiert das Double-Submit-Cookie-Pattern dagegen:

- Bei `POST`/`PUT`/`PATCH`/`DELETE` **und** vorhandenem `session_id`-Cookie
  muss der Request-Header `X-CSRF-Token` exakt dem Wert des `csrf_token`-
  Cookies entsprechen, sonst `403`.
- Ohne `session_id`-Cookie (z. B. `/login`, `/register` selbst) wird der
  Check automatisch übersprungen - es gibt noch nichts zu schützen, da ein
  Angreifer ohne gültige Session auf keinen echten Endpoint zugreifen kann.
- Das Frontend liest `csrf_token` per JavaScript aus `document.cookie`
  (`apps/frontend/lib/api-client.ts`) und spiegelt ihn bei jedem
  mutierenden Request als Header zurück - ein Angreifer auf einer fremden
  Domain kann dieses Cookie nicht auslesen (Same-Origin-Policy), sein
  gefälschter Request hat also nie den korrekten Header-Wert.

## Netzwerk-Exposition

- Von den Compose-Services darf **nur `caddy`** (Ports 80/443) öffentlich
  erreichbar sein. `frontend`, `api`, `postgres`, `redis`, `qdrant` und
  `minio` binden ihre Host-Port-Mappings in `docker-compose.yml` standardmäßig
  an `${BIND_ADDRESS:-127.0.0.1}` statt an `0.0.0.0` - sie sind also nur vom
  Host selbst (z. B. per SSH-Tunnel) erreichbar, nicht über die öffentliche
  Netzwerkschnittstelle. `caddy` routet intern über das Docker-Netzwerk
  (`api:8000`, `frontend:3000`, siehe `infra/caddy/Caddyfile`) und braucht
  dafür keine Host-Port-Mappings der Zielservices.
- Für lokale Entwicklung, bei der direkter externer Zugriff auf einen
  einzelnen Service nötig ist, kann `BIND_ADDRESS=0.0.0.0` in `.env` gesetzt
  werden (siehe `.env.example`). **Für Produktivbetrieb auf einem öffentlich
  erreichbaren Host darf `BIND_ADDRESS` niemals auf `0.0.0.0` gesetzt werden**
  - das exponiert API/Datenbank/Cache/Vektorstore/Objektspeicher ohne
  Auth-Schutz direkt im Internet.
- Hintergrund: Ein direkt exponierter Port ist ein reales Angriffsziel -
  automatisierte Scanner senden dauerhaft generische Exploit-Payloads
  (WordPress-Pfade, Path-Traversal, XSS, Kubernetes-API-Pfade usw.) gegen
  jeden offenen Port, unabhängig davon, welche Anwendung tatsächlich dahinter
  läuft.

## Transport-Sicherheit

- Lokal terminiert Caddy HTTP ohne Zertifikat (`infra/caddy/Caddyfile`,
  `:80`-Block).
- Für Produktion die auskommentierte Domain-Variante in der Caddyfile
  aktivieren - Caddy holt dann automatisch ein Let's-Encrypt-Zertifikat und
  erzwingt HTTPS.
- Interner Verkehr (API ↔ Postgres/Redis/Qdrant/MinIO) läuft unverschlüsselt
  im Docker-internen Netz, was für ein Single-Host-Deployment akzeptabel
  ist. Bei einem Multi-Host-Setup sollte dieser Verkehr zusätzlich per
  VPN/Overlay-Netzwerk abgesichert werden.
- `SESSION_COOKIE_SECURE` (`.env`) **muss** auf `true` stehen, sobald die App
  wirklich über HTTPS ausgeliefert wird (Produktion) - sonst schickt der
  Browser das Session-Cookie theoretisch auch über eine ungesicherte
  HTTP-Verbindung mit. Lokal über `http://localhost` **muss** der Wert
  dagegen `false` sein, sonst verwirft der Browser das Cookie beim Setzen
  komplett und der Login schlägt fehl (Cookies mit `Secure`-Attribut werden
  nur über HTTPS akzeptiert).

## Secrets

- Alle Secrets kommen ausschließlich aus Umgebungsvariablen (`.env`), nie
  hartkodiert im Code.
- `.env` ist in `.gitignore` ausgeschlossen; nur `.env.example` (ohne echte
  Werte) wird versioniert.
- Die Default-Werte in `.env.example` (`POSTGRES_PASSWORD=notebook`,
  `MINIO_ROOT_PASSWORD=minio-password`) sind ausschließlich für lokale
  Entwicklung gedacht und **müssen** vor jedem Produktivbetrieb geändert
  werden.

## Datenzugriff / Mandantentrennung

- Jede Notebook-Operation (Sources, Chat, Notes) prüft über
  `assert_can_access()`, ob der angemeldete User Zugriff auf das
  angefragte Notebook hat, bevor irgendeine Datenbank- oder
  Qdrant-Operation ausgeführt wird.
- Die Qdrant-Suche ist immer mit einem `notebook_id`-Filter versehen -
  ein Chat in Notebook A kann strukturell keine Chunks aus Notebook B
  zurückbekommen, selbst bei einem Bug in der Score-Heuristik.
- MinIO-Objekte sind nie öffentlich lesbar; Downloads laufen ausschließlich
  über zeitlich begrenzte signierte URLs.

## Logging

`apps/api/app/core/logging.py` / `apps/worker/app/core/logging.py`
konfigurieren strukturiertes Logging. Es werden bewusst **keine**
Dokumenteninhalte, Chat-Antworten oder Secrets geloggt - nur IDs, Status,
Fehlermeldungen und technische Metadaten (Latenz, Modellname). Das
`langdock_requests`-Audit-Tracking speichert ebenfalls nur Metadaten
(Modell, Latenz, Tokenzahl), keine Prompt-/Antwortinhalte.

## Upload-Validierung

- `apps/api/app/sources/upload.py` erlaubt ausschließlich eine feste Liste
  an MIME-Types/Extensions (PDF, DOCX, TXT, Markdown, HTML, CSV, XLSX) und
  validiert den tatsächlichen Dateiinhalt (nicht nur die vom Client
  gesendete Content-Type-Angabe).
- `MAX_UPLOAD_SIZE_MB` begrenzt die Dateigröße serverseitig, unabhängig vom
  Frontend.

## Bekannte Lücken (für Produktivbetrieb zu schließen)

- Kein Audit-Log-Review-UI (die `audit_events`-Tabelle existiert im
  Datenmodell, wird aber im MVP noch nicht befüllt).
- Kein Passwort-Reset-Flow (E-Mail-Versand ist im MVP nicht vorgesehen) -
  ein vergessenes Passwort erfordert aktuell einen manuellen DB-Eingriff.
- `notebook_members`-basiertes Sharing (siehe Auth-Abschnitt oben) ist im
  Datenmodell vorbereitet, aber im MVP nicht aktiv.

Rate-Limiting (Login, Redis-Fixed-Window) und CSRF-Schutz
(Double-Submit-Cookie) sind seit der Session-Auth-Migration umgesetzt, siehe
Abschnitte oben.
