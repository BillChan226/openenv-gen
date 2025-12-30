# Jira (Generated)

## Docker (canonical)

The canonical Docker Compose files for this repo are:

- `docker/docker-compose.yml` (production-like: nginx serves the built frontend)
- `docker/docker-compose.dev.yml` (dev: Vite + backend with source mounts)

### Preflight: verify Docker daemon is running

Most Docker errors during verification are caused by the Docker daemon not running / not reachable.

Run:

```bash
docker info
```

If this fails with something like:

```
Cannot connect to the Docker daemon ... Is the docker daemon running?
```

Start Docker Desktop (or your Docker daemon) and retry.

### Build + run + health check

```bash
docker compose -f docker/docker-compose.yml build

docker compose -f docker/docker-compose.yml up -d

# backend health (host port is configurable via BACKEND_HOST_PORT)
curl -fsS http://localhost:${BACKEND_HOST_PORT:-8000}/health
```

### Dev stack

```bash
docker compose -f docker/docker-compose.dev.yml up -d --build

# If you run the Vite dev server locally (outside Docker), it proxies /api to http://localhost:8000.
# If you run it in Docker, use mode=docker so the proxy targets the backend service name:
#   npm run dev -- --mode docker
```

### Database init / schema changes (repeatable)

This repo includes a **repeatable** DB init/seed step:

- `db_init` service runs `app/database/init/01_schema.sql` + `02_seed.sql` on every `docker compose up`.
- The SQL is written to be **idempotent** (safe to re-run).

This avoids relying on Postgres `/docker-entrypoint-initdb.d` first-boot behavior (which only runs when the data volume is empty).

#### Resetting the DB volume (optional)

If you want a completely fresh database (e.g., to remove all data), reset the volume:

```bash
docker compose -f docker/docker-compose.yml down -v
# or
docker compose -f docker/docker-compose.dev.yml down -v
```

Then re-run `up --build`.

## Non-Docker verification (fallback)

If you cannot run Docker in your environment, you can still run a basic verification that:

- installs backend dependencies
- starts the backend locally
- checks `GET /health`

From the repo root:

```bash
npm run verify
```

Notes:

- This does **not** start Postgres; it only verifies the backend process can boot and serve `/health`.
- You can override the port via `PORT=8001 npm run verify`.

## Notes

- The root-level `docker/` directory contains Dockerfiles and nginx config, but **does not** contain supported compose files.
- Compose files intentionally omit the obsolete `version:` key (modern Docker Compose ignores it and warns).
