#!/usr/bin/env bash
set -euo pipefail

# Aggressive cleanup for a compose project. Useful if compose state is corrupted.
#
# Usage:
#   COMPOSE_PROJECT_NAME=foodhub docker/compose-reset.sh
#   # or, to match compose-up default naming:
#   docker/compose-reset.sh foodhub_1700000000

PROJECT_NAME="${1:-${COMPOSE_PROJECT_NAME:-foodhub}}"

echo "Resetting compose project: ${PROJECT_NAME}"

if [[ -f "./docker-compose.yml" ]]; then
  docker compose -p "${PROJECT_NAME}" down --remove-orphans --volumes || true
  docker compose -p "${PROJECT_NAME}" rm -f -s -v || true
else
  docker compose -p "${PROJECT_NAME}" -f docker/docker-compose.yml down --remove-orphans --volumes || true
  docker compose -p "${PROJECT_NAME}" -f docker/docker-compose.yml rm -f -s -v || true
fi

cat <<'EOF'
If you still see stale container-id errors, clear local compose cache (host-level):
  rm -rf ~/.docker/compose
EOF
