import { spawn } from 'node:child_process';
import net from 'node:net';

function getEnv(name, fallback) {
  const v = process.env[name];
  return v == null || v === '' ? fallback : v;
}

async function findFreePort(preferred = 3000) {
  const tryPort = (port) =>
    new Promise((resolve) => {
      const server = net.createServer();
      server.unref();
      server.on('error', () => resolve(null));
      server.listen({ port, host: '127.0.0.1' }, () => {
        const address = server.address();
        server.close(() => resolve(address.port));
      });
    });

  // Try preferred first, then a small range, then 0 (ephemeral)
  const candidates = [preferred];
  for (let p = preferred + 1; p <= preferred + 50; p += 1) candidates.push(p);

  for (const p of candidates) {
    // eslint-disable-next-line no-await-in-loop
    const ok = await tryPort(p);
    if (ok) return ok;
  }

  const ephemeral = await tryPort(0);
  if (!ephemeral) throw new Error('Unable to find a free port');
  return ephemeral;
}

function waitForHttp(url, timeoutMs = 30_000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = async () => {
      try {
        const res = await fetch(url, { redirect: 'follow' });
        if (res.ok) return resolve(true);
      } catch {
        // ignore
      }
      if (Date.now() - started > timeoutMs) {
        return reject(new Error(`Timed out waiting for ${url}`));
      }
      setTimeout(attempt, 300);
    };
    attempt();
  });
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: 'inherit',
      shell: process.platform === 'win32',
      ...opts,
    });
    child.on('exit', (code) => {
      if (code === 0) return resolve(0);
      return reject(new Error(`${cmd} ${args.join(' ')} exited with code ${code}`));
    });
  });
}

async function main() {
  const preferredPort = Number(getEnv('VITE_PORT', '3000'));
  const port = await findFreePort(preferredPort);
  const baseURL = getEnv('PLAYWRIGHT_BASE_URL', `http://localhost:${port}`);

  // Ensure Playwright uses the same baseURL and Vite uses the chosen port.
  const env = {
    ...process.env,
    VITE_PORT: String(port),
    PLAYWRIGHT_BASE_URL: baseURL,
  };

  console.log(`[qa-e2e] Using VITE_PORT=${env.VITE_PORT}`);
  console.log(`[qa-e2e] Using PLAYWRIGHT_BASE_URL=${env.PLAYWRIGHT_BASE_URL}`);

  // Start Vite dev server.
  // Ensure Vite can write its dep cache even if node_modules was created by root (e.g. via Docker).
  // Vite respects XDG_CACHE_HOME for its cache directory.
  const envWithCache = {
    ...env,
    // Avoid writing into node_modules/.vite which may be owned by root in some environments.
    // Vite uses this env var for its cache dir.
    VITE_CACHE_DIR: env.VITE_CACHE_DIR || `${process.cwd()}/.cache/vite`,
  };

  const vite = spawn(
    process.platform === 'win32' ? 'npm.cmd' : 'npm',
    ['run', 'dev'],
    {
      stdio: 'inherit',
      env: envWithCache,
    },
  );

  const shutdown = async () => {
    if (!vite.killed) {
      vite.kill('SIGTERM');
    }
  };

  process.on('SIGINT', async () => {
    await shutdown();
    process.exit(130);
  });
  process.on('SIGTERM', async () => {
    await shutdown();
    process.exit(143);
  });

  try {
    await waitForHttp(`${baseURL}/`, 45_000);
    await run(
      process.platform === 'win32' ? 'npx.cmd' : 'npx',
      ['playwright', 'test'],
      { env: envWithCache },
    );
  } finally {
    await shutdown();
  }
}

main().catch((err) => {
  console.error(`[qa-e2e] ${err?.stack || err}`);
  process.exit(1);
});
