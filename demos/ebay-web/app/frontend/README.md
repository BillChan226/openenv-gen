# ebay-web frontend

## Install

This project uses Vite + React.

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## E2E / smoke tests (Playwright)

The repo includes Playwright-based browser tests under `tests/e2e/`.

### Run against a locally running frontend

1) Start the app (and backend if you want real API data):

```bash
npm run dev
```

2) In another terminal:

```bash
# Install Playwright browsers (one-time per machine/CI image)
npx playwright install --with-deps

# Run e2e tests against the dev server
PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run test:e2e
```

### Run in CI / constrained environments

- The frontend includes Playwright **only for E2E tests** (`@playwright/test` in `devDependencies`).
- If you do not need E2E tests, you can skip Playwright browser downloads during install:

```bash
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
npm install
```

(You can still run the app; only E2E tests require the browsers.)

## E2E (Playwright) QA

This repo includes a Playwright-based E2E suite that verifies:
- Navigation between primary pages
- Key interactive flows (search, cart, wishlist/account where available)
- No unexpected JS console errors
- No unexpected network failures (4xx/5xx)
- Basic accessibility smoke checks (axe-core)

### Run locally

From `app/frontend`:

```bash
npm ci
npx playwright install --with-deps

# Option A: Playwright starts Vite automatically (recommended)
npm run test:e2e

# Option B: QA runner that starts Vite on a free port then runs Playwright
npm run test:e2e:qa
```

### Environment variables
- `PLAYWRIGHT_BASE_URL`: if set, Playwright will not start Vite and will run against this URL.
- `VITE_PORT`: port used when starting Vite (default 5173).

