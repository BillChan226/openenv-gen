import { test, expect } from '@playwright/test';

// Default to local dev backend. In Docker, set E2E_BACKEND_URL=http://backend:3000
const backendBase = process.env.E2E_BACKEND_URL || 'http://localhost:8002';

async function waitForBackendHealthy() {
  const url = `${backendBase}/health`;
  const started = Date.now();
  const timeoutMs = 60_000;
  // Simple polling without extra deps
  // eslint-disable-next-line no-constant-condition
  while (true) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // ignore
    }
    if (Date.now() - started > timeoutMs) {
      throw new Error(`Backend did not become healthy within ${timeoutMs}ms: ${url}`);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
}

test.describe('E2E smoke', () => {
  test('frontend loads, nav works, search works, no console/network errors', async ({ page }) => {
    await waitForBackendHealthy();

    const consoleErrors: string[] = [];
    const requestFailures: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore common benign errors from browser extensions / favicon / source maps
        if (
          /favicon\.ico/i.test(text) ||
          /Failed to load resource/i.test(text) ||
          /net::ERR_/i.test(text)
        ) {
          return;
        }
        consoleErrors.push(text);
      }
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    page.on('requestfailed', (req) => {
      const failure = req.failure();
      const url = req.url();
      // Ignore favicon failures and similar non-critical assets
      if (/\/favicon\.ico(\?|$)/i.test(url)) return;
      requestFailures.push(`${req.method()} ${url} :: ${failure?.errorText || 'unknown error'}`);
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.getByTestId('welcome-text')).toBeVisible();
    await expect(page.getByTestId('nav-home-logo')).toBeVisible();
    await expect(page.getByTestId('header-search-input')).toBeVisible();

    // Navigate to Advanced Search
    await page.getByTestId('nav-advanced-search').click();
    await expect(page).toHaveURL(/\/advanced-search/);

    // Navigate to Cart
    await page.getByTestId('nav-cart').click();
    await expect(page).toHaveURL(/\/cart/);

    // Back home
    await page.getByTestId('nav-home-logo').click();
    await expect(page).toHaveURL(/\/$/);

    // Search flow (goes to /category/all?q=...)
    await page.getByTestId('header-search-input').fill('camera');
    await page.getByTestId('header-search-submit').click();
    await expect(page).toHaveURL(/\/category\/all\?q=camera/);

    // Ensure page renders some kind of results container or empty state
    // Category page uses product cards; we assert at least the heading exists.
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Assert no console errors / request failures
    expect(consoleErrors, `Console errors:\n${consoleErrors.join('\n')}`).toEqual([]);
    expect(requestFailures, `Request failures:\n${requestFailures.join('\n')}`).toEqual([]);
  });
});
