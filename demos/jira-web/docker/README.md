# Docker

This repo’s Docker Compose files live under the repo root `docker/` directory:

- `docker/docker-compose.yml` (production-like stack: nginx + backend + db)
- `docker/docker-compose.dev.yml` (development stack)

## Prerequisites

- Docker Desktop / Docker Engine running
- Docker Compose v2 (`docker compose ...`)

Verify Docker is available:

```bash
docker info
```

If you see an error like:

- `Cannot connect to the Docker daemon ...`

…it means Docker is not running (environmental), not a repo issue.

## Quick start (from repo root)

### Production-like stack

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d

# backend health (default host port is 8000; see compose file)
curl -fsS http://localhost:${BACKEND_HOST_PORT:-8000}/health
```

### Development stack

```bash
docker compose -f docker/docker-compose.dev.yml build
docker compose -f docker/docker-compose.dev.yml up
```

## Useful commands

```bash
# view resolved config
docker compose -f docker/docker-compose.yml config

# logs
docker compose -f docker/docker-compose.yml logs -f

# stop
docker compose -f docker/docker-compose.yml down

# stop + remove volumes (forces DB init scripts to re-run on next up)
docker compose -f docker/docker-compose.yml down -v
```

## Healthchecks

The compose stack includes service healthchecks so you can deterministically verify readiness once Docker is available.

- Backend: `GET /health` should return 200
