#!/usr/bin/env bash
# Wait until a TCP host:port becomes reachable, then optionally exec a command.
#
# Usage:
#   ./wait-for-it.sh host:port [-t timeout] [-- command args...]
#
# Docker Compose already uses healthchecks + depends_on/condition for
# service ordering (see docker-compose.yml). This script is kept as a
# standalone helper for contexts without Compose orchestration, e.g. CI
# pipelines or manual container runs against an external Postgres/Redis.

set -euo pipefail

TIMEOUT=30
HOST_PORT=""
CMD=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t)
      TIMEOUT="$2"
      shift 2
      ;;
    --)
      shift
      CMD=("$@")
      break
      ;;
    *)
      if [[ -z "$HOST_PORT" ]]; then
        HOST_PORT="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$HOST_PORT" ]]; then
  echo "Usage: $0 host:port [-t timeout] [-- command args...]" >&2
  exit 1
fi

HOST="${HOST_PORT%%:*}"
PORT="${HOST_PORT##*:}"

start_ts=$(date +%s)
until (exec 3<>"/dev/tcp/${HOST}/${PORT}") 2>/dev/null; do
  now_ts=$(date +%s)
  if (( now_ts - start_ts >= TIMEOUT )); then
    echo "Timeout after ${TIMEOUT}s waiting for ${HOST}:${PORT}" >&2
    exit 1
  fi
  echo "Waiting for ${HOST}:${PORT}..."
  sleep 1
done
exec 3>&- 2>/dev/null || true

echo "${HOST}:${PORT} is available."

if [[ ${#CMD[@]} -gt 0 ]]; then
  exec "${CMD[@]}"
fi
