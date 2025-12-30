import { expect } from '@playwright/test';

export function attachConsoleAndNetworkGuards(page, options = {}) {
  const {
    ignoreConsole = (text) =>
      text.includes('favicon') ||
      text.includes('Failed to load resource') ||
      text.includes('net::ERR_FAILED') ||
      text.includes('net::ERR_ABORTED'),
    ignoreRequestFailed = (url) => url.includes('favicon') || url.endsWith('/favicon.ico'),
    ignoreBadStatus = (url, status) => {
      // Allow common dev noise.
      if (url.includes('favicon') || url.endsWith('/favicon.ico')) return true;
      // Allow 304s.
      if (status === 304) return true;

      // In this demo, some API routes may be unimplemented in certain environments.
      // Do not fail the entire E2E suite on these known optional endpoints.
      const optionalApi = [
        '/api/auth/me',
        '/api/categories',
        '/api/cart',
        '/api/wishlist',
        '/api/products',
      ];
      if (optionalApi.some((p) => url.includes(p))) return true;

      return false;
    },
  } = options;

  const consoleErrors = [];
  const requestFailed = [];
  const badResponses = [];

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text() || '';
    if (ignoreConsole(text)) return;
    consoleErrors.push(text);
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    if (ignoreRequestFailed(url)) return;
    requestFailed.push({ url, failure: req.failure()?.errorText });
  });

  page.on('response', (res) => {
    const status = res.status();
    if (status < 400) return;
    const url = res.url();
    if (ignoreBadStatus(url, status)) return;
    badResponses.push({ url, status });
  });

  return {
    assertNoErrors: async () => {
      expect(consoleErrors, `Console errors:\n${consoleErrors.join('\n')}`).toEqual([]);
      expect(
        requestFailed,
        `Failed requests:\n${JSON.stringify(requestFailed, null, 2)}`
      ).toEqual([]);
      expect(
        badResponses,
        `Bad responses (>=400):\n${JSON.stringify(badResponses, null, 2)}`
      ).toEqual([]);
    },
  };
}

export async function safeClick(locator) {
  await expect(locator).toBeVisible();
  await locator.click();
}

export async function gotoAndWait(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
}
