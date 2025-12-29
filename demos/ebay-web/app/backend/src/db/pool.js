import pg from 'pg';
import { config } from '../config/env.js';
import { logger } from '../utils/logger.js';

const { Pool } = pg;

let pool = null;

export function getPool() {
  if (!pool) {
    if (!config.DATABASE_URL) {
      throw new Error('DATABASE_URL not configured');
    }
    pool = new Pool({ connectionString: config.DATABASE_URL });
    pool.on('error', (err) => {
      logger.error('Postgres pool error', { message: err.message });
    });
  }
  return pool;
}

export async function tryQuery(text, params = []) {
  const p = getPool();
  return p.query(text, params);
}
