#!/usr/bin/env bash
# Trigger a Qdrant snapshot of the "notebook_chunks" collection via the
# Qdrant HTTP API and download it to a local backup directory.
#
# Usage (from repo root, with the stack running):
#   ./infra/backup/backup_qdrant.sh

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

QDRANT_URL="${QDRANT_HOST_URL:-http://localhost:6333}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-notebook_chunks}"

mkdir -p "${OUTPUT_DIR}"
timestamp="$(date +%Y%m%d_%H%M%S)"

echo "Requesting snapshot for collection '${QDRANT_COLLECTION}' at ${QDRANT_URL}"
snapshot_name="$(curl -sf -X POST "${QDRANT_URL}/collections/${QDRANT_COLLECTION}/snapshots" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['name'])")"

outfile="${OUTPUT_DIR}/qdrant_${QDRANT_COLLECTION}_${timestamp}.snapshot"
echo "Downloading snapshot '${snapshot_name}' -> ${outfile}"
curl -sf "${QDRANT_URL}/collections/${QDRANT_COLLECTION}/snapshots/${snapshot_name}" -o "${outfile}"

echo "Done: ${outfile}"
