import pg from 'pg';
import { config } from '../config/env.js';
import { createLogger } from '../utils/logger.js';

const { Pool } = pg;

const logger = createLogger(config.LOG_LEVEL);

const pool = new Pool({
  connectionString: config.DATABASE_URL,
  // Fail fast on misconfiguration; callers can retry.
  connectionTimeoutMillis: parseInt(process.env.PGCONNECT_TIMEOUT_MS || '3000', 10),
  keepAlive: true,
});

export async function waitForDbReady({
  retries = parseInt(process.env.DB_CONNECT_RETRIES || '10', 10),
  delayMs = parseInt(process.env.DB_CONNECT_DELAY_MS || '1000', 10),
} = {}) {
  let lastErr;
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      await pool.query('SELECT 1');
      return true;
    } catch (err) {
      lastErr = err;
      logger.warn('Database not ready yet', {
        attempt,
        retries,
        message: err.message,
      });
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }

  logger.error('Database did not become ready in time', {
    message: lastErr?.message,
  });
  return false;
}

// Optional slow query logging in development
if (config.NODE_ENV === 'development') {
  const originalQuery = pool.query.bind(pool);
  pool.query = async (...args) => {
    const start = Date.now();
    const res = await originalQuery(...args);
    const duration = Date.now() - start;
    if (duration > 150) {
      logger.debug('Slow query', {
        duration,
        sql: typeof args[0] === 'string' ? args[0].slice(0, 300) : 'prepared',
      });
    }
    return res;
  };
}

export default pool;
