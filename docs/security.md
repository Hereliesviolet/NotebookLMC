# Security

This describes what the code does today, including the gaps. It is not a
security audit.

## Authentication

E-mail and password login with server-side sessions. The code is in
`apps/api/app/core/security.py` (hashing, `get_current_user`),
`core/sessions.py` (Redis session store) and `auth/router.py` (`/register`,
`/login`, `/logout`, `/me`).

**Passwords.** Argon2 through `argon2-cffi` (`PasswordHasher`, salted per
hash). The only rule is a minimum length, `MIN_PASSWORD_LENGTH` (default 10),
in line with NIST 800-63B's advice against composition rules.

**Sessions.** A successful `POST /api/auth/login` creates a Redis entry
`session:<opaque id>` mapping to the user id, with a sliding TTL of
`SESSION_TTL_SECONDS` (each successful check extends it). Two cookies are set:

- `session_id`: `httpOnly`, `SameSite=Lax`, `Secure` if `SESSION_COOKIE_SECURE`
  is true.
- `csrf_token`: same attributes but readable by JavaScript, see CSRF below.

`get_current_user` reads only the `session_id` cookie, looks it up in Redis and
loads the user from Postgres. `POST /api/auth/logout` deletes the Redis entry
and both cookies.

**Rate limiting.** `core/rate_limit.py` uses Redis fixed-window counters
(`INCR` + `EXPIRE`) and returns 429 with a `Retry-After` header:

- login: 5 attempts per 60 seconds per IP and e-mail combination
- registration: 5 attempts per 300 seconds per IP (no e-mail in the key, since
  no account exists yet)

The IP is `request.client.host`. Nothing in the repository configures trusted
proxy headers, so behind Caddy this is most likely the proxy's address and all
clients would share one counter. This has not been verified against a running
deployment.

**Roles and sharing.** There is no sharing between users.
`notebooks/service.py::assert_can_access()` only compares the notebook's
`owner_id` with the caller.

**Local development.** `make seed` creates the demo user from
`DEV_DEMO_USER_*`. There is no automatic dev login.

## CSRF

Cookie-based auth makes CSRF relevant. `CsrfMiddleware`
(`core/middleware.py`) implements double-submit protection:

- For `POST`, `PUT`, `PATCH` and `DELETE` requests that carry a `session_id`
  cookie, the `X-CSRF-Token` header must equal the `csrf_token` cookie, else
  the API answers 403.
- Requests without a `session_id` cookie skip the check; without a session
  there is nothing to protect (this covers `/login` and `/register`).
- The frontend reads the `csrf_token` cookie in `lib/api-client.ts` and sends
  it as the header on every mutating request. A third-party site cannot read
  the cookie, so a forged request lacks the matching header.

## Network exposure

- Only `caddy` (80/443) is meant to be public. `frontend`, `api`, `postgres`,
  `redis`, `qdrant` and `minio` publish their ports on
  `${BIND_ADDRESS:-127.0.0.1}`, so they are reachable from the host only (for
  example through an SSH tunnel). Caddy reaches `api:8000` and `frontend:3000`
  over the Docker network.
- `BIND_ADDRESS=0.0.0.0` is for local development only. On a publicly
  reachable host it exposes the API, database, cache, vector store and object
  store to the internet.

## Transport

- Locally, Caddy serves plain HTTP on `:80` (`infra/caddy/Caddyfile`).
- For production, enable the commented domain block in the Caddyfile. Caddy
  then obtains a Let's Encrypt certificate and redirects to HTTPS.
- Traffic between the containers is unencrypted on the Docker network. That is
  acceptable for one host; across hosts it needs a VPN or overlay network.
- Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS. Over plain
  `http://localhost` it must be `false`, or the browser drops the cookie and
  login fails.

## Secrets

- Secrets come from environment variables (`.env`), not from code.
- `.env` is git-ignored; `.env.example` holds placeholders only.
- The defaults in `.env.example` (`POSTGRES_PASSWORD=notebook`,
  `MINIO_ROOT_PASSWORD=minio-password`, `DEV_DEMO_USER_PASSWORD`) are for local
  use and must be changed for any real deployment.

## Data access

- Notebook operations (sources, chat, notes, studio) call `assert_can_access()`
  before touching the database or Qdrant.
- Every Qdrant search is filtered on `notebook_id`, so a chat in one notebook
  cannot retrieve chunks from another one even if the ranking logic had a bug.
- Citation validation checks that cited chunks and sources belong to the
  notebook, see [rag-pipeline.md](rag-pipeline.md).
- The MinIO bucket is created with anonymous access disabled. There is no
  download endpoint for original files at the moment.

## Logging

`core/logging.py` (API and worker) configures structured logging. Document
contents, chat answers and secrets are not logged, only ids, status, error
messages and technical metadata such as latency and model name. The
`langdock_requests` table stores metadata only.

## Upload validation

- `sources/upload.py` allows a fixed set of file types (PDF, DOCX, TXT,
  Markdown, HTML, CSV, XLSX). The type is derived from the file extension
  first, then from the guessed MIME type, then from the content type the
  client sent. The file content is not inspected (no magic-byte check); a file
  that cannot be parsed ends up with status `failed`.
- `MAX_UPLOAD_SIZE_MB` (default 50) is enforced on the server, and empty files
  are rejected.
- The upload is read into memory before the size check.

## Known gaps

- No password reset and no e-mail verification. A forgotten password needs a
  manual database change.
- No notebook sharing.
- `audit_events` exists as a table but is never written.
- The CSRF token comparison is a plain string comparison, not constant-time.
- Rate limiting keys on the peer IP, see above.
- No security headers on the API itself; Caddy sets `X-Content-Type-Options`,
  `X-Frame-Options` and `Referrer-Policy` in the local Caddyfile.
