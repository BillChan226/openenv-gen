# Docker Setup (ebay-web)

This project ships two Docker Compose configurations:

- **Production-like**: `docker/compose.prod.yml`
  - Frontend is served by **nginx** and reverse-proxies `/api/*` to the backend (same-origin; no CORS).
  - Best for demos.

- **Development (hot reload)**: `docker/compose.dev.yml`
  - Frontend runs **Vite dev server** with HMR.
  - Backend runs with **nodemon**.

## Ports (host)

These ports are chosen to avoid common conflicts:

- Frontend (prod): **http://localhost:3002**
- Frontend (dev / Vite): **http://localhost:5173**
- Backend API (direct): **http://localhost:8002**
- Env adapter (OpenEnv): **http://localhost:9101**
- Postgres (NOT published by default; internal only)

> If any port is already in use on your machine, edit the `ports:` mappings in the compose files.

## URLs

- Storefront UI (prod): `http://localhost:3002/`
- Storefront UI (dev): `http://localhost:5173/`
- Backend health: `http://localhost:8002/health`
- Backend API base: `http://localhost:8002/api/*`
- Env adapter OpenAPI: `http://localhost:9101/openapi.json`
- Env adapter health: `http://localhost:9101/health`

## Production-like run

From repo root:

```bash
docker compose -f docker/compose.prod.yml up -d --build
```

Then open:
- UI: http://localhost:3002

### Prod smoke test

```bash
# API health (direct)
curl -fsS http://localhost:8002/health

# Frontend (nginx) should respond (200/304)
curl -I http://localhost:3002/

# Env adapter (optional in CI; should respond when running)
curl -fsS http://localhost:9101/health
```

### Browser-based verification (required for acceptance)

Run the repeatable verification script (captures compose output + runs Playwright smoke tests that assert **no console errors** and **no failed network requests**):

```bash
./scripts/verify_prod.sh
```

Artifacts:
- `./screenshots/compose-prod-up.log` (compose up output)
- `app/frontend/playwright-report/` (HTML report)


## Development (hot reload)

```bash
docker compose -f docker/compose.dev.yml up --build
```

- UI: http://localhost:5173
- API: http://localhost:8002

### Dev smoke test

```bash
# API health
curl -fsS http://localhost:8002/health

# Frontend (Vite) should respond (200/304)
curl -I http://localhost:5173/
```

## Database initialization

Postgres loads schema/seed automatically on first init via:

- `../app/database/init:/docker-entrypoint-initdb.d:ro`

If you change SQL and need to re-run init scripts:

```bash
docker compose -f docker/compose.prod.yml down -v
# or
docker compose -f docker/compose.dev.yml down -v
```

## Notes

- In **prod**, the browser calls `/api/*` on the frontend origin, and nginx proxies to the backend container.
- In **dev**, Vite proxies `/api/*` to the backend container.
- The env adapter is configured to talk to the backend and frontend via Docker service names (NOT `localhost`).
