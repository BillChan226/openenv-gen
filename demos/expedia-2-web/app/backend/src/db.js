import pg from 'pg';
import { env } from './config/env.js';
import { createMemoryDb } from './memory/db.js';

const { Pool } = pg;

let mode = env.DB_MODE || (env.DATABASE_URL ? 'postgres' : 'memory');

let pool = null;
let memory = null;
let postgresHealthy = false;

function ensureMemory() {
  if (!memory) {
    memory = createMemoryDb();
    // eslint-disable-next-line no-undef
    console.log('[db] Using in-memory DB (set DB_MODE=postgres and DATABASE_URL to use Postgres)');
  }
}

async function initPostgres() {
  if (!env.DATABASE_URL) throw new Error('DATABASE_URL is not set');
  pool = new Pool({ connectionString: env.DATABASE_URL });

  // Probe connection once so environments without Docker/psql can still run.
  try {
    await pool.query('SELECT 1 AS ok');
    postgresHealthy = true;
  } catch (e) {
    postgresHealthy = false;
    try {
      await pool.end();
    } catch {
      // ignore
    }
    pool = null;
    throw e;
  }
}

// Initialize selected mode but gracefully fall back to memory if Postgres is unreachable.
if (mode === 'postgres') {
  try {
    await initPostgres();
  } catch (e) {
    // eslint-disable-next-line no-undef
    console.warn(`[db] Postgres unavailable (${e.message}). Falling back to in-memory DB.`);
    mode = 'memory';
    ensureMemory();
  }
} else {
  ensureMemory();
}

export { pool };

export async function query(text, params) {
  if (mode === 'postgres') return pool.query(text, params);
  ensureMemory();
  return memory.query(text, params);
}

export async function withTransaction(fn) {
  if (mode === 'postgres') {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const result = await fn(client);
      await client.query('COMMIT');
      return result;
    } catch (e) {
      await client.query('ROLLBACK');
      throw e;
    } finally {
      client.release();
    }
  }

  ensureMemory();
  return memory.withTransaction(fn);
}

export const dbMode = mode;
export const dbStatus = () => ({ mode, postgresHealthy });
