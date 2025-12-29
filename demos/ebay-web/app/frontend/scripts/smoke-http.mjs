const baseURL = process.env.SMOKE_BASE_URL || process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:13000';
const apiBaseURL = process.env.SMOKE_API_BASE_URL || 'http://localhost:18000';

async function check(path, { expectStatus = 200, mustContain, base = baseURL, timeoutMs = 8000 } = {}) {
  const url = new URL(path, base).toString();

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  let res;
  let text;
  try {
    res = await fetch(url, { redirect: 'follow', signal: controller.signal });
    text = await res.text();
  } catch (e) {
    const msg = e?.name === 'AbortError' ? `Timed out after ${timeoutMs}ms` : (e?.message || String(e));
    throw new Error(`[smoke] Request failed for ${url}: ${msg}`);
  } finally {
    clearTimeout(t);
  }

  if (res.status !== expectStatus) {
    throw new Error(`Expected ${expectStatus} for ${url}, got ${res.status}. Body: ${text.slice(0, 200)}`);
  }

  if (mustContain) {
    const ok =
      mustContain instanceof RegExp
        ? mustContain.test(text)
        : typeof mustContain === 'string'
          ? text.includes(mustContain)
          : false;

    if (!ok) {
      const expected = mustContain instanceof RegExp ? mustContain.toString() : String(mustContain);
      throw new Error(`Response for ${url} did not include expected content: ${expected}`);
    }
  }

  return { url, status: res.status };
}

async function main() {
  const rootDivRegex = /<div\s+id=["']root["']\s*>/i;

  const checks = [
    // Frontend app shell
    () => check('/', { mustContain: rootDivRegex }),
    // SPA routes should also return the app shell
    () => check('/login', { mustContain: rootDivRegex }),
    () => check('/cart', { mustContain: rootDivRegex }),
    () => check('/wishlist', { mustContain: rootDivRegex }),

    // Backend health + key API endpoints used by the frontend
    () => check('/health', { base: apiBaseURL }),
    () => check('/api/catalog', { base: apiBaseURL }),
    () => check('/api/catalog/items?limit=1', { base: apiBaseURL }),
  ];

  for (const run of checks) {
    const { url, status } = await run();
    // eslint-disable-next-line no-console
    console.log(`[smoke] OK ${status} ${url}`);
  }
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error('[smoke] FAILED', err);
  process.exit(1);
});
