# ebay-web

## Frontend dev server (deterministic port for QA)

The frontend is configured to run on **http://localhost:5173**.

- Vite config: `app/frontend/vite.config.js` uses `port: 5173` and `strictPort: true`.
- Default scripts also pin port 5173.

### Start frontend

```bash
npm install
npm run dev
```

If port 5173 is already in use, Vite will **fail fast** (strictPort) instead of silently switching to another port.

### Optional port override

If you must run on a different port, set `VITE_PORT`:

```bash
VITE_PORT=5174 npm run dev
```

Playwright tests also respect `VITE_PORT`.

## Docker

This repo includes multiple Docker Compose configurations:

- **Production-like (nginx + same-origin /api proxy)**: `docker/compose.prod.yml`
- **Development (hot reload)**: `docker/compose.dev.yml` (preferred for local dev)
- **Legacy root compose**: `docker-compose.yml` (dev-oriented)

### Idempotent `docker compose up`

Compose files in this repo intentionally **do not** set `container_name:` so that:

- `docker compose up -d` is safely re-runnable
- multiple Compose projects can run side-by-side without container name conflicts

If you want predictable names, use a project name:

```bash
docker compose -p ebay-web -f docker/docker-compose.yml up -d
```

Cleanup / reset:

```bash
docker compose -f docker/docker-compose.yml down -v --remove-orphans
```

### Production-like run (recommended for demos)

From repo root:

```bash
docker compose -f docker/compose.prod.yml down -v --remove-orphans
docker compose -f docker/compose.prod.yml up -d --build
```

Health checks:

```bash
curl -fsS http://localhost:8002/health
curl -I http://localhost:3002/
```

### Production verification (browser-based; required for acceptance)

```bash
./scripts/verify_prod.sh
```

Stop:

```bash

### Verification (build + run + health + smoke)

To consistently prove the acceptance criterion (images build successfully), run:

```bash
make verify
```

This executes:
- `docker compose -f docker/docker-compose.yml build`
- `docker compose -f docker/docker-compose.yml up -d`
- `curl -fsS http://localhost:18000/health`
- `node app/frontend/scripts/smoke-http.mjs` (defaults to `http://localhost:13000`; override with `SMOKE_BASE_URL`)


docker compose -f docker/compose.prod.yml down
```


## Docker dev (hot reload)

This repo includes a dev compose file that runs:

- Postgres
- Backend with **nodemon** auto-reload
- Frontend with **Vite HMR**

### Start

From repo root:

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

### URLs

- Frontend (Vite): http://localhost:5173
- Backend API: http://localhost:8002/health

### Verify hot reload

- Frontend HMR: edit any file under `app/frontend/src/` (e.g. `App.jsx`) and the browser should update without a full rebuild.
- Backend reload: edit any file under `app/backend/src/` and the backend container should restart; `curl -f http://localhost:8002/health` should continue returning 200 after the restart.


### Browser-based verification checklist (QA rubric)

After `docker compose -f docker/docker-compose.dev.yml up --build`:

1) Open **http://localhost:5173** in a browser.
2) Open DevTools:
   - Console: confirm **no red errors** during initial load and navigation.
   - Network: confirm no unexpected **4xx/5xx** responses.
3) Exercise core flows end-to-end against the running backend:
   - Navigate between pages via header links (Home, Cart, Wishlist, Account).
   - Use search (header search / advanced search) and confirm results render.
   - Add an item to Cart, change quantity, remove item.
   - Toggle Wishlist items.
   - Sign in (if seeded credentials exist) and visit Account pages.
4) Confirm hot reload:
   - Edit a React component under `app/frontend/src/` and verify the browser updates.
   - Edit a backend route under `app/backend/src/` and verify `GET http://localhost:8002/health` returns 200 after restart.

### Stop

```bash
docker compose -f docker/docker-compose.dev.yml down
```


### Docker dev smoke test (no browser tooling required)

From repo root:

```bash
./scripts/smoke-dev.sh
```

This will:

- `docker compose -f docker/docker-compose.dev.yml up -d --build`
- wait for backend `GET /health` (default: http://localhost:8002/health)
- wait for frontend `GET /` (default: http://localhost:5173/)
- perform a basic API reachability check

Optional overrides:

```bash
BACKEND_PORT=8002 FRONTEND_PORT=5173 ./scripts/smoke-dev.sh
# If you already started the stack:
SKIP_UP=1 ./scripts/smoke-dev.sh
```

## OpenEnv adapter (HTTP API for automated verification)

The OpenEnv adapter is a small FastAPI service that proxies to the backend (and optionally checks frontend reachability).

### Configure

Environment variables:

- `EBAY_WEB_BACKEND_URL` (or `BACKEND_URL`): backend base URL (default: `http://localhost:18000`)
- `EBAY_WEB_FRONTEND_URL` (or `FRONTEND_URL`): frontend base URL (default: `http://localhost:3000`)
- `OPENENV_HTTP_TIMEOUT`: upstream timeout seconds (default: `20`)
- `OPENENV_PORT`: adapter port (default: `19000`)

### Run

```bash
python -m env.openenv_adapter
```

### Endpoints

All endpoints return JSON.

Meta:

- `GET /health` → always `200` with `{ ok: true }` (no upstream calls)
- `GET /health/details` → includes reachability checks for backend and frontend

UI:

- `POST /navigate` body: `{ "route": "/" }`
  - Returns `200` when the frontend is reachable.
  - Returns `502` with a detailed diagnostic payload when the frontend is unreachable.

Catalog / Search:

- `GET /catalog/categories`
- `GET /catalog/products` (supports `limit`, `offset`, and also `page`/`perPage` which are mapped to `limit`/`offset`)
- `GET /catalog/category/{slug}/products`
- `POST /search/advanced` (structured payload; proxied to backend `/api/catalog/search/advanced`)

Cart:

- `GET /cart`
- `POST /cart/items/add` body: `{ "productId": "...", "quantity": 1 }`
- `POST /cart/items/remove` body: `{ "productId": "..." }` (also accepts `cartItemId` and maps it to `productId`)

Auth / Account / Wishlist:

- `GET /session`
- `POST /auth/sign-in`
- `POST /auth/sign-out`
- `GET /wishlist`
- `POST /wishlist/toggle`
- `GET /account/summary`

## QA / verification (no browser_* tooling required)

This repo includes a minimal **Playwright** smoke test suite that covers:

- App loads
- Navigation works (Cart, Wishlist, Home)
- No console errors
- No failed network requests (basic)
- Basic accessibility smoke checks

### Run E2E smoke tests (single command, works even if 3000 is occupied)

From `app/frontend/`:

```bash
npm run test:e2e:qa
```

This command:

- picks a free port (prefers `VITE_PORT` if set, otherwise starts at 3000)
- starts the Vite dev server on that port
- runs Playwright against the matching `PLAYWRIGHT_BASE_URL`
- shuts the dev server down when finished

Optional overrides:

```bash
VITE_PORT=3002 npm run test:e2e:qa
# or
PLAYWRIGHT_BASE_URL=http://localhost:3002 npm run test:e2e:qa
```


### Run E2E tests from the dedicated runner (app/e2e)

If you want to run the E2E suite directly from `app/e2e/` (instead of via the frontend helper script), make sure you install dependencies in that folder so the Playwright CLI is available locally:

```bash
npm ci
npm run version
npm run install:browsers
npm test
```

Notes:
- The E2E runner uses `npx playwright ...` so it does **not** require a globally installed `playwright` binary.
- Browser installation can take a few minutes the first time.

### HTTP-only smoke test (no browser required)

If you cannot run Playwright (or want a fast deterministic check), run:

```bash
npm run test:smoke:http
```

This validates that the app shell is served for key SPA routes (`/`, `/login`, `/cart`, `/wishlist`).

If using a non-default port:

```bash
VITE_PORT=5174 npm run dev
VITE_PORT=5174 npm run test:e2e
```

### Notes

- Tests live in `app/frontend/tests/e2e/`.
- Playwright config: `app/frontend/playwright.config.js`.
