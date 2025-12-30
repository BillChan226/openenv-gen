#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker CLI not found in PATH." >&2
  exit 127
fi

# This checks both client and daemon connectivity.
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is not reachable." >&2
  echo "- If you're on macOS/Windows: start Docker Desktop" >&2
  echo "- If you're on Linux: start the docker service (e.g., sudo systemctl start docker)" >&2
  echo "Then re-run your docker compose command." >&2
  exit 1
fi

echo "OK: Docker daemon reachable."