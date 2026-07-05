#!/usr/bin/env bash
# Mirror the MinIO "notebook-files" bucket to a local backup directory using
# the MinIO Client (mc), run via a throwaway `minio/mc` container so no local
# mc install is required.
#
# Usage (from repo root, with the stack running):
#   ./infra/backup/backup_minio.sh

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

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minio}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio-password}"
MINIO_BUCKET="${MINIO_BUCKET:-notebook-files}"
NETWORK_NAME="${MINIO_NETWORK_NAME:-notebooklmc_default}"

timestamp="$(date +%Y%m%d_%H%M%S)"
target_dir="${OUTPUT_DIR}/minio_${MINIO_BUCKET}_${timestamp}"
mkdir -p "${target_dir}"

echo "Mirroring bucket '${MINIO_BUCKET}' from ${MINIO_ENDPOINT} -> ${target_dir}"
docker run --rm \
  --network "${NETWORK_NAME}" \
  -v "${target_dir}:/backup" \
  --entrypoint /bin/sh \
  minio/mc:latest \
  -c "mc alias set backup-src '${MINIO_ENDPOINT}' '${MINIO_ROOT_USER}' '${MINIO_ROOT_PASSWORD}' && mc mirror backup-src/${MINIO_BUCKET} /backup"

echo "Done: ${target_dir}"
