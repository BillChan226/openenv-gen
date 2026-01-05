#!/usr/bin/env bash
set -euo pipefail

# Cleanup helper for local Docker Compose runs.
# Fixes common issues:
# - orphan container with no name (e.g. ID 909e9ebe4cc0)
# - other concurrently-running stacks with conflicting container names/ports

PROJECT_NAME="expedia"

echo "==> Stopping compose stack: ${PROJECT_NAME}"
docker compose -p "${PROJECT_NAME}" -f "$(dirname "$0")/docker-compose.yml" down --remove-orphans || true

echo "==> Removing any containers matching ${PROJECT_NAME}-* (if any)"
# shellcheck disable=SC2046
if docker ps -aq --filter "name=^/${PROJECT_NAME}-" | grep -q .; then
  docker rm -f $(docker ps -aq --filter "name=^/${PROJECT_NAME}-") || true
fi

echo "==> If you have a specific orphan container ID, remove it explicitly"
echo "    Example: docker rm -f 909e9ebe4cc0"

echo "==> Done. You can now run: docker compose -f docker/docker-compose.yml up --build"
