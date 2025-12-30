import { spawn } from 'node:child_process';
import process from 'node:process';

const BACKEND_PORT = process.env.PORT ? Number(process.env.PORT) : 8000;
const BACKEND_URL = process.env.BACKEND_URL || `http://localhost:${BACKEND_PORT}`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(url, { timeoutMs = 2000 } = {}) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    return res;
  } finally {
    clearTimeout(t);
  }
}

async function waitForHealth({ retries = 40, delayMs = 250 } = {}) {
  const url = `${BACKEND_URL}/health`;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetchWithTimeout(url, { timeoutMs: 2000 });
      if (res.ok) return true;
    } catch {
      // ignore
    }
    await sleep(delayMs);
  }
  return false;
}

function startBackend() {
  const child = spawn('npm', ['start'], {
    cwd: new URL('../app/backend/', import.meta.url),
    stdio: 'inherit',
    env: {
      ...process.env,
      NODE_ENV: process.env.NODE_ENV || 'test',
      PORT: String(BACKEND_PORT),
      // Allow running without a DB in verification environments.
      // The backend /health endpoint can be configured to return 200 even if DB is down.
      ALLOW_NO_DB: process.env.ALLOW_NO_DB || '1',
      DATABASE_URL: process.env.DATABASE_URL || '',
      FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:5173',
      JWT_SECRET: process.env.JWT_SECRET || 'dev-secret',
      LOG_LEVEL: process.env.LOG_LEVEL || 'info',
    },
  });

  return child;
}

async function main() {
  console.log(`[verify] Starting backend (non-Docker) on port ${BACKEND_PORT}...`);

  // Ensure deps are present; if npm ci fails, verification should fail.
  const npmCi = spawn('npm', ['ci'], {
    cwd: new URL('../app/backend/', import.meta.url),
    stdio: 'inherit',
    env: process.env,
  });
  const ciCode = await new Promise((resolve) => npmCi.on('exit', resolve));
  if (ciCode !== 0) {
    console.error('[verify] npm ci failed');
    process.exit(ciCode || 1);
  }

  const backend = startBackend();

  const cleanup = () => {
    if (!backend.killed) backend.kill('SIGTERM');
  };
  process.on('SIGINT', () => {
    cleanup();
    process.exit(130);
  });
  process.on('SIGTERM', () => {
    cleanup();
    process.exit(143);
  });

  const ok = await waitForHealth();
  if (!ok) {
    console.error(`[verify] Backend health check failed: ${BACKEND_URL}/health`);
    cleanup();
    process.exit(1);
  }

  console.log(`[verify] OK: GET ${BACKEND_URL}/health`);

  // Run backend unit tests if present (does not require DB).
  const npmTest = spawn('npm', ['test'], {
    cwd: new URL('../app/backend/', import.meta.url),
    stdio: 'inherit',
    env: process.env,
  });
  const testCode = await new Promise((resolve) => npmTest.on('exit', resolve));

  cleanup();
  process.exit(testCode || 0);
}

main().catch((err) => {
  console.error('[verify] Unexpected error', err);
  process.exit(1);
});
