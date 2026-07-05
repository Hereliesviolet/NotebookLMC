# shared-types

Canonical TypeScript interfaces for the API contracts between `apps/frontend`
and `apps/api` (Notebook, Source, Message, Citation, ChatResponse, Note, User).

`apps/frontend/lib/types.ts` currently mirrors these types manually because
the frontend's Docker build context (`./apps/frontend`, see
`docker-compose.yml`) does not include `packages/`. If the project moves to
an npm/pnpm workspace with a repo-root Docker build context, `apps/frontend`
should depend on this package directly instead of duplicating the types.
