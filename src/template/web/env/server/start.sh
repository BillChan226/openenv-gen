#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}

# Wait for frontend and backend to be ready
echo "Waiting for frontend..."
until curl -sf http://frontend:3000 > /dev/null 2>&1; do
    sleep 1
done
echo "Frontend is ready"

echo "Waiting for backend..."
until curl -sf http://backend:5000/api/health > /dev/null 2>&1; do
    sleep 1
done
echo "Backend is ready"

# Start the environment server
exec python -m uvicorn env.server.app:app --host 0.0.0.0 --port "${PORT}"
