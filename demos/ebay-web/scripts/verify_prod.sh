#!/usr/bin/env bash
set -euo pipefail

# Repeatable verification for production Docker Compose.
# Acceptance criteria:
# - Compose builds/starts from a clean state
# - Frontend reachable in browser
# - Backend reachable and healthy
# - Core flows work against backend
# - No JS console errors and no failed network requests during interactions

COMPOSE_FILE="docker/compose.prod.yml"
FRONTEND_URL="http://localhost:3002"
BACKEND_HEALTH_URL="http://localhost:8002/health"

say() { printf "\n[%s] %s\n" "$(date +%H:%M:%S)" "$*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

wait_http_ok() {
  local url="$1"
  local name="$2"
  local max_seconds="${3:-60}"

  say "Waiting for ${name} (${url}) to return HTTP 200 (timeout ${max_seconds}s)"
  local start
  start=$(date +%s)
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      say "OK: ${name} is reachable"
      return 0
    fi
    local now
    now=$(date +%s)
    if (( now - start > max_seconds )); then
      echo "Timed out waiting for ${name} at ${url}" >&2
      return 1
    fi
    sleep 2
  done
}

say "Checking prerequisites"
require_cmd docker
require_cmd curl

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is not available. Install Docker Desktop / Compose v2." >&2
  exit 1
fi

say "Bringing stack down (volumes removed)"
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans

say "Building + starting stack"
# Capture output to help diagnose intermittent failures.
LOG_DIR="./screenshots"
mkdir -p "$LOG_DIR"
UP_LOG="$LOG_DIR/compose-prod-up.log"
set +e
(docker compose -f "$COMPOSE_FILE" up -d --build) 2>&1 | tee "$UP_LOG"
UP_EXIT=${PIPESTATUS[0]}
set -e

if [[ $UP_EXIT -ne 0 ]]; then
  say "ERROR: docker compose up failed. Capturing logs..."
  docker compose -f "$COMPOSE_FILE" ps || true
  docker compose -f "$COMPOSE_FILE" logs --no-color --tail=200 || true
  echo "Compose up output saved to: $UP_LOG" >&2
  exit $UP_EXIT
fi

say "Compose is up. Showing status"
docker compose -f "$COMPOSE_FILE" ps

wait_http_ok "$BACKEND_HEALTH_URL" "backend /health" 90
wait_http_ok "$FRONTEND_URL/" "frontend" 90

say "Running browser-based smoke (Playwright) against prod stack"
# Uses the frontend's existing Playwright tests. These tests assert:
# - No console errors
# - No failed network requests
# - Core navigation flows
#
# We run them from the frontend workspace (host), pointing at the prod frontend.
require_cmd node

pushd app/frontend >/dev/null
npm ci
PLAYWRIGHT_BASE_URL="$FRONTEND_URL" npx playwright install --with-deps
PLAYWRIGHT_BASE_URL="$FRONTEND_URL" npx playwright test
popd >/dev/null

say "PASS: prod stack verified (frontend + backend + browser smoke)"
