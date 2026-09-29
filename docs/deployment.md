# Deployment

The stack is defined in `docker-compose.yml`. Commands below assume Docker
Compose v2 and are run from the repository root.

## Local

```bash
cp .env.example .env
# set LANGDOCK_API_KEY, LANGDOCK_PRIMARY_MODEL, LANGDOCK_FAST_MODEL
docker compose up -d --build
docker compose exec api alembic upgrade head
```

`make env`, `make up` and `make migrate` do the same. `make seed` creates a
demo user.

Published ports (bound to `BIND_ADDRESS`, default `127.0.0.1`; Caddy uses 80
and 443):

| Service | Port |
| --- | --- |
| Frontend | 3000 |
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Qdrant | 6333 |
| MinIO (S3 API / console) | 9000 / 9001 |

## Access without Caddy

The frontend contains a catch-all route handler,
`apps/frontend/app/api/[...path]/route.ts`. It forwards `/api/*` on the
server side to `INTERNAL_API_URL` (default `http://api:8000`) with query
string, body, headers and cookies, and streams the response back, including
binary exports (PDF, DOCX, PNG). With it the app works on port 3000 alone:

```bash
docker compose up -d --build frontend api   # caddy stays down
curl http://localhost:3000/api/health
```

It replaced a `rewrites()` entry in `next.config.mjs`. The rewrites proxy has
a fixed timeout and cut off long studio generations (30-60 s and more) with
`socket hang up`, while the API kept working and finished. The route handler
sets its own timeout, `PROXY_TIMEOUT_MS` in `route.ts` (310 s), slightly above
the Gunicorn `--timeout 300` in `apps/api/Dockerfile` so that Gunicorn's own
error response arrives first.

`INTERNAL_API_URL` is read at runtime; changing it needs no image rebuild. The
handler is not a replacement for Caddy in production (TLS, security headers).

## Caddy

`infra/caddy/Caddyfile` serves `:80` by default, sends `/api/*` to `api:8000`
and everything else to `frontend:3000`. For production, enable the commented
domain block at the end of the file: Caddy then fetches a Let's Encrypt
certificate automatically. Frontend and API need no change as long as `/api`
stays a path prefix on the same origin.

## Sharing an existing Caddy

If another Caddy container already holds ports 80/443 on the host, the
project's own `caddy` service cannot start and stays in state `Created`. Use
the overlay `docker-compose.shared-caddy.yml` instead:

```bash
docker compose stop caddy && docker compose rm -f caddy
docker compose -f docker-compose.yml -f docker-compose.shared-caddy.yml \
  up -d --no-deps api frontend
```

Always name the services explicitly on such a host; a bare `docker compose up
-d` would start the project's `caddy` again.

Setup:

1. In the overlay, set the external network `caddy_network` to the network the
   existing Caddy is attached to
   (`docker inspect <caddy-container> --format '{{json .NetworkSettings.Networks}}'`).
2. Add a site block to the existing Caddy's Caddyfile that routes `/api/*` to
   `api:8000` and everything else to `frontend:3000`, as in
   `infra/caddy/Caddyfile`. Validate and reload it
   (`caddy validate`, `caddy reload`).
3. Point the domain's DNS at the host before enabling the block, or the
   Let's Encrypt challenge fails. Check both the A and the AAAA record: a
   stale AAAA record pointing to a different host makes IPv6 clients see the
   other host's certificate even though the A record is right. Until a real
   domain exists, a `http://`-prefixed block on a placeholder host name runs
   without automatic HTTPS (`example.com` is refused by ACME).

Two problems the overlay works around:

- **Alias collisions.** Once `api` is in the shared network, short names such
  as `postgres` or `minio` can also belong to other projects' containers there,
  and Docker's DNS may resolve them to the wrong one (observed: `api` connected
  to another project's Postgres and failed to authenticate). The overlay
  therefore points `api` at the unique `container_name` values
  (`notebook-postgres`, `notebook-redis`, `notebook-qdrant`, `notebook-minio`).
- **Next.js bind address.** The standalone server binds to the address its
  `HOSTNAME` resolves to. With two networks that can be the wrong one, so the
  overlay sets `HOSTNAME=0.0.0.0`.

## Frontend build variable

`NEXT_PUBLIC_API_URL` is inlined into the JavaScript bundle at build time, so
it is a build argument in `docker-compose.yml`, not an environment variable.
After changing it, rebuild:

```bash
docker compose build frontend
docker compose up -d frontend
```

Leave it empty (default). The frontend then calls relative paths such as
`/api/notebooks`, which reach the API through Caddy or the route handler on
the same origin. That also works from other devices, where an absolute
`http://localhost:8000` would point at the device itself.

Set an absolute URL only if the API runs on a separate domain. The browser
then makes cross-origin requests, and `APP_URL` must be the frontend origin.

## `APP_URL`

`APP_URL` is only used for CORS (`allow_origins` in `apps/api/app/main.py`). It
matters for cross-origin access to the API: a `npm run dev` frontend on port
3000 talking directly to the API on 8000, or a separate API domain. In the
same-origin setup (empty `NEXT_PUBLIC_API_URL`) there is no CORS and the
value is irrelevant. When the public domain changes, update it.

## Migrations

Only the `api` service runs Alembic; the worker reads and writes the same
tables but never issues DDL.

```bash
make migrate                          # upgrade head
make migrate-autogenerate msg="..."   # new revision from model changes
```

## Backups

Scripts in `infra/backup/`, each writing to `infra/backup/output/`
(git-ignored):

- `backup_postgres.sh`: `pg_dump` in custom format, gzip-compressed
- `backup_minio.sh`: `mc mirror` of the `notebook-files` bucket (throwaway
  `minio/mc` container)
- `backup_qdrant.sh`: snapshot of the `notebook_chunks` collection via the
  Qdrant HTTP API

Scheduling, retention and off-host copies are not part of the repository. Keep
`.env` somewhere safe as well.

## Operations

- **Workers.** More worker containers can be started; RQ distributes jobs over
  all workers listening on the same queues. Today all jobs go to the `default`
  queue, see [architecture.md](architecture.md).
- **Health checks.** `postgres`, `redis`, `qdrant` and `minio` have Compose
  health checks, and `api` and `worker` wait for them. The API has
  `GET /api/health`.
- **Statelessness.** API and worker keep no local state, and sessions are in
  Redis, so the API can run with several workers or replicas without sticky
  sessions. The Gunicorn worker count is `API_WORKERS` (default 4).

## Troubleshooting

- **Port 80/443 already in use:** `docker compose up caddy` fails with `port is
  already allocated`. Stop the other proxy, map Caddy to other ports in
  `docker-compose.yml` (for example `"8080:80"`), or use the shared-Caddy
  overlay above. Frontend (3000) and API (8000) stay reachable meanwhile.
- **`caddy` stuck in `Created`:** same cause; remove it with `docker compose
  stop caddy && docker compose rm -f caddy` and use the overlay.
- **Login works but the session is lost:** `SESSION_COOKIE_SECURE` must be
  `false` on plain HTTP and `true` on HTTPS, see [security.md](security.md).

## Settings to check before a real deployment

Full list with comments: [`.env.example`](../.env.example).

- `LANGDOCK_API_KEY`, `LANGDOCK_PRIMARY_MODEL`, `LANGDOCK_FAST_MODEL`
- `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `DEV_DEMO_USER_PASSWORD`
  (defaults are for local use)
- `SESSION_COOKIE_SECURE=true` behind HTTPS
- `APP_URL` only for cross-origin setups
- `NEXT_PUBLIC_API_URL`: normally empty; a rebuild is needed after changing it
- `BIND_ADDRESS`: keep `127.0.0.1` on a public host
