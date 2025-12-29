#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker/docker-compose.dev.yml"

BACKEND_PORT="${BACKEND_PORT:-8002}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# Allow skipping compose up if caller already started the stack.
SKIP_UP="${SKIP_UP:-0}"

wait_http() {
  local url="$1"
  local name="$2"
  local attempts="${3:-60}"

  echo "[smoke] waiting for ${name}: ${url}"
  for i in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null; then
      echo "[smoke] ${name} is up"
      return 0
    fi
    sleep 2
  done

  echo "[smoke] ERROR: timed out waiting for ${name} (${url})" >&2
  return 1
}

if [[ "${SKIP_UP}" != "1" ]]; then
  echo "[smoke] bringing up dev stack: ${COMPOSE_FILE}"
  docker compose -f "${COMPOSE_FILE}" up -d --build --quiet-pull
fi

echo "[smoke] docker compose ps"
docker compose -f "${COMPOSE_FILE}" ps

wait_http "http://localhost:${BACKEND_PORT}/health" "backend /health"
wait_http "http://localhost:${FRONTEND_PORT}/" "frontend /"

# Validate frontend returns HTML (non-empty)
HTML_HEAD="$(curl -fsS "http://localhost:${FRONTEND_PORT}/" | head -n 5)"
if [[ -z "${HTML_HEAD}" ]]; then
  echo "[smoke] ERROR: frontend returned empty response" >&2
  exit 1
fi

echo "[smoke] frontend response head:"
echo "${HTML_HEAD}"

# Validate API endpoint reachable from host (ensures backend is serving API)
# This does not prove browser->backend networking, but combined with Vite proxy config it validates wiring.
if ! curl -fsS "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
  echo "[smoke] NOTE: /api/health not found; trying /api/items as a generic check" >&2
  curl -fsS "http://localhost:${BACKEND_PORT}/api/items" >/dev/null
else
  echo "[smoke] backend /api/health OK"
fi

echo "[smoke] PASS"
