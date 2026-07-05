#!/usr/bin/env bash
# Dump the PostgreSQL database of the NotebookLM clone via pg_dump.
#
# Usage (from repo root, with the stack running):
#   ./infra/backup/backup_postgres.sh
#
# Reads connection settings from the repo's .env (POSTGRES_*). Writes a
# timestamped, gzip-compressed custom-format dump to infra/backup/output/,
# which can be restored with `pg_restore`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
ENV_FILE="${REPO_ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-notebook}"
POSTGRES_USER="${POSTGRES_USER:-notebook}"
CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-notebook-postgres}"

mkdir -p "${OUTPUT_DIR}"
timestamp="$(date +%Y%m%d_%H%M%S)"
outfile="${OUTPUT_DIR}/postgres_${POSTGRES_DB}_${timestamp}.dump.gz"

echo "Dumping database '${POSTGRES_DB}' from container '${CONTAINER_NAME}' -> ${outfile}"
docker exec "${CONTAINER_NAME}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc | gzip > "${outfile}"

echo "Done: ${outfile}"
echo "Restore with: gunzip -c ${outfile} | docker exec -i ${CONTAINER_NAME} pg_restore -U ${POSTGRES_USER} -d ${POSTGRES_DB} --clean --if-exists"
