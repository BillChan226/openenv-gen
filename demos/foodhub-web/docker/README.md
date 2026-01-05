# Docker Compose troubleshooting

If `docker compose up` fails with an error like:

> `No such container: <id>` when recreating

This is typically **Docker Compose project state corruption** on the host (Compose is trying to recreate a container ID that no longer exists).

## Quick workaround (recommended)

Run compose with a **fresh project name**:

```bash
docker compose -p foodhub_$(date +%s) -f docker/docker-compose.yml up --build
```

If you are using the root compose file:

```bash
docker compose -p foodhub_$(date +%s) up --build
```

## Cleanup commands

Try these cleanup commands before re-running:

```bash
docker compose -f docker/docker-compose.yml down --remove-orphans --volumes
# Remove stopped containers created by this compose file
docker compose -f docker/docker-compose.yml rm -f -s -v
```

If the issue persists, remove Compose v2 cache (if present):

```bash
rm -rf ~/.docker/compose
```

## Notes

- This repository intentionally does **not** set a top-level `name:` and does **not** pin `container_name:` to avoid cross-run conflicts.
- In CI/harness environments, consider setting a unique `COMPOSE_PROJECT_NAME` per run.
