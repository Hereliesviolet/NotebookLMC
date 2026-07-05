# Security

## Auth (aktueller MVP-Stand)

Es gibt **keine echte Nutzer-Authentifizierung**. `apps/api/app/core/security.py`
implementiert eine Dev-/Demo-Auth:

- Beim ersten `POST /api/auth/login` wird - falls nicht vorhanden - ein
  Demo-User (`DEV_DEMO_USER_EMAIL`) angelegt und ein opakes Token
  (`dev:<user_id>`) zurückgegeben.
- `get_current_user` (in `apps/api/app/core/deps.py`) liest das Token aus dem
  `Authorization: Bearer ...`-Header, dekodiert die User-ID und lädt den
  User aus Postgres - ohne Signaturprüfung.
- Das Frontend führt beim ersten Laden automatisch einen Login durch
  (`AuthGate`-Komponente) und speichert das Token in `localStorage`.

Das ist **ausschließlich für lokale Entwicklung/Demo geeignet** und muss vor
einem echten Produktivbetrieb mit mehreren Nutzern ersetzt werden. Die
Austauschstelle ist bewusst klein gehalten:

1. `get_current_user` durch eine echte Token-Validierung (z. B. OIDC/Entra ID
   JWT-Verifikation) ersetzen.
2. `issue_dev_token`/`/api/auth/login` durch den echten SSO-Redirect-Flow
   ersetzen.
3. `notebook_members` (bereits im Datenmodell vorhanden) für
   rollenbasierten Zugriff auf gemeinsame Notebooks nutzen - aktuell prüft
   `notebooks/service.py::assert_can_access()` nur Besitzerschaft
   (`owner_id`), der Member-Mechanismus ist als Erweiterung vorbereitet.

`DEV_AUTH_ENABLED=false` ist als Schalter in `.env.example` vorbereitet, um
in einer zukünftigen Auth-Implementierung den Dev-Login-Pfad hart abschalten
zu können.

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

- Kein Rate-Limiting auf API-Ebene (nur implizit über Langdock-seitige
  Limits und Worker-Queue-Concurrency).
- Kein CSRF-Schutz nötig, da die API zustandslos per Bearer-Token statt
  Cookies arbeitet - bei einer Umstellung auf Cookie-basierte Sessions wäre
  das nachzurüsten.
- Kein Audit-Log-Review-UI (die `audit_events`-Tabelle existiert im
  Datenmodell, wird aber im MVP noch nicht befüllt).
