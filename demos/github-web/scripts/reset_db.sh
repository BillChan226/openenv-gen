#!/usr/bin/env bash
# Reset database to initial state
set -euo pipefail

CONTAINER_NAME="${1:-database}"

echo "Resetting database in container: $CONTAINER_NAME"

docker exec "$CONTAINER_NAME" psql -U postgres -d {{ENV_NAME}}_db -c "SELECT reset_environment();"

echo "Database reset complete!"
