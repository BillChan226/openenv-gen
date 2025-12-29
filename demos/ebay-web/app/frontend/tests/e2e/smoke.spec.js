import { test, expect } from '@playwright/test';

test('app loads and shows header search', async ({ page }) => {
  const consoleErrors = [];
  const failedRequests = [];

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text() || '';
    // Ignore common non-fatal missing asset noise in dev.
    if (text.includes('favicon') || text.includes('Failed to load resource')) return;
    consoleErrors.push(text);
  });

  page.on('requestfailed', (req) => {
    failedRequests.push({ url: req.url(), failure: req.failure()?.errorText });
  });

  await page.goto('/', { waitUntil: 'domcontentloaded' });

  // Basic UI presence checks
  await expect(page.getByTestId('header-search-input')).toBeVisible();
  await expect(page.getByTestId('header-search-submit')).toBeVisible();

  // Ensure no obvious runtime issues
  // Note: Vite dev server may request /favicon.ico (or other assets) which can be 404 in this demo.
  // We treat those as non-fatal for smoke testing.
  const ignorable = (url) => url.includes('favicon') || url.endsWith('/favicon.ico');

  expect(consoleErrors, `Console errors: ${consoleErrors.join('\n')}`).toEqual([]);
  expect(
    failedRequests.filter((r) => !ignorable(r.url)),
    `Failed requests: ${JSON.stringify(failedRequests, null, 2)}`
  ).toEqual([]);
});

test('navigation links work', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  // Cart
  await page.getByTestId('nav-cart').click();
  await expect(page).toHaveURL(/\/cart/);

  // Wishlist (via top bar "My Wish List")
  await page.getByTestId('nav-my-wishlist').click();
  // If auth is required, app may redirect to /login with next param.
  await expect(page).toHaveURL(/\/(account\/wishlist|login\?next=%2Faccount%2Fwishlist)/);

  // Home
  await page.getByTestId('nav-home-logo').click();
  await expect(page).toHaveURL(/\/$/);
});
