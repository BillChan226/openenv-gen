#!/usr/bin/env bash
set -euo pipefail

# Workaround for some Docker Compose environments where the compose project state
# becomes stale/corrupted and `docker compose up` fails during container recreate
# with errors like:
#   Error: No such container: <container_id>
#
# Strategy: run compose with a unique project name per invocation unless the user
# explicitly sets COMPOSE_PROJECT_NAME.

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-foodhub_$(date +%s)}"

echo "Using COMPOSE_PROJECT_NAME=${PROJECT_NAME}"

# Prefer the repo-root compose file if present (some harnesses expect it).
if [[ -f "./docker-compose.yml" ]]; then
  docker compose -p "${PROJECT_NAME}" up --build "$@"
else
  docker compose -p "${PROJECT_NAME}" -f docker/docker-compose.yml up --build "$@"
fi
