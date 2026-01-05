const { Pool } = require('pg');

let pool;
let dbAvailableCache = null;
let dbAvailableCacheAt = 0;

function isConnectionRefusedError(err) {
  if (!err) return false;
  const msg = String(err.message || '');
  return (
    err.code === 'ECONNREFUSED' ||
    err.code === 'ENOTFOUND' ||
    err.code === 'EHOSTUNREACH' ||
    err.code === 'ETIMEDOUT' ||
    msg.includes('ECONNREFUSED') ||
    msg.includes('connect ECONNREFUSED')
  );
}

function getPool() {
  if (pool) return pool;

  // Prefer a full DATABASE_URL when provided (works for local Postgres or managed DBs)
  if (process.env.DATABASE_URL) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.PGSSLMODE === 'require' ? { rejectUnauthorized: false } : undefined,
      max: Number(process.env.DB_POOL_MAX || 10),
      idleTimeoutMillis: Number(process.env.DB_IDLE_TIMEOUT_MS || 30000),
      connectionTimeoutMillis: Number(process.env.DB_CONN_TIMEOUT_MS || 2000),
    });
    return pool;
  }

  // Fallback to discrete env vars.
  // Defaults are Docker-friendly but also work locally if you set DB_HOST=localhost.
  // If running outside Docker and DB_HOST isn't explicitly set, default to 127.0.0.1.
  // This avoids Node resolving 'localhost' to IPv6 ::1 and failing when Postgres only
  // listens on IPv4 (common in some environments), causing ECONNREFUSED ::1:5432.
  const defaultHost = process.env.DB_HOST || (process.env.DOCKER ? 'db' : '127.0.0.1');

  pool = new Pool({
    host: defaultHost,
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER || 'expedia',
    password: process.env.DB_PASSWORD || process.env.DB_PASS || 'expedia',
    database: process.env.DB_NAME || 'expedia',
    ssl: process.env.PGSSLMODE === 'require' ? { rejectUnauthorized: false } : undefined,
    max: Number(process.env.DB_POOL_MAX || 10),
    idleTimeoutMillis: Number(process.env.DB_IDLE_TIMEOUT_MS || 30000),
    connectionTimeoutMillis: Number(process.env.DB_CONN_TIMEOUT_MS || 2000),
  });

  return pool;
}

async function query(text, params) {
  const p = getPool();
  return p.query(text, params);
}

async function isAvailable() {
  const ttlMs = Number(process.env.DB_AVAILABLE_CACHE_MS || 2000);
  const now = Date.now();

  if (dbAvailableCache !== null && now - dbAvailableCacheAt < ttlMs) {
    return dbAvailableCache;
  }

  try {
    const p = getPool();
    await p.query('SELECT 1');
    dbAvailableCache = true;
    dbAvailableCacheAt = now;
    return true;
  } catch (err) {
    // Don't spam logs for common "DB is down" scenarios.
    if (!isConnectionRefusedError(err)) {
      // eslint-disable-next-line no-console
      console.warn('DB availability check failed:', err.message);
    }
    dbAvailableCache = false;
    dbAvailableCacheAt = now;
    return false;
  }
}

module.exports = {
  getPool,
  query,
  isAvailable,
};
