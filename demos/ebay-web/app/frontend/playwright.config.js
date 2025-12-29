import { defineConfig, devices } from '@playwright/test';

const port = Number(process.env.VITE_PORT) || 3000;

// Base URL resolution:
// - If PLAYWRIGHT_BASE_URL (or E2E_BASE_URL) is provided, use it.
// - Otherwise, when running inside docker-compose, the frontend service container is
//   named "ebay-web-frontend-1" by default (compose v2). Using this makes e2e runs
//   deterministic without requiring env vars.
// - Fallback to localhost for local dev.
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ||
  process.env.E2E_BASE_URL ||
  (process.env.DOCKER_COMPOSE ? 'http://ebay-web-frontend-1' : `http://localhost:${port}`);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
