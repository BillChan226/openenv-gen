import dotenv from 'dotenv';

dotenv.config();

// In local/dev environments (including automated verification), we allow
// sensible defaults so the server can boot even if no .env is provided.
// Production deployments should provide real secrets/DB URLs.
const required = ['JWT_SECRET'];
for (const key of required) {
  if (!process.env[key] && process.env.NODE_ENV === 'production') {
    throw new Error(`Missing required environment variable: ${key}`);
  }
}

function isTruthy(v) {
  return ['1', 'true', 'yes', 'on'].includes(String(v || '').toLowerCase());
}

function buildDatabaseUrlFromParts() {
  // Support multiple env var naming conventions:
  // - DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME (app)
  // - PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE (pg)
  // - POSTGRES_* (docker)
  const host = process.env.DB_HOST || process.env.PGHOST || process.env.POSTGRES_HOST || 'localhost';
  const port = process.env.DB_PORT || process.env.PGPORT || process.env.POSTGRES_PORT || '5432';
  const user = process.env.DB_USER || process.env.PGUSER || process.env.POSTGRES_USER || 'jira';
  const password = process.env.DB_PASSWORD || process.env.PGPASSWORD || process.env.POSTGRES_PASSWORD || 'jira';
  const database = process.env.DB_NAME || process.env.PGDATABASE || process.env.POSTGRES_DB || 'jira';

  const ssl = isTruthy(process.env.DB_SSL || process.env.PGSSLMODE);
  const sslMode = ssl ? '?sslmode=require' : '';

  return `postgresql://${encodeURIComponent(user)}:${encodeURIComponent(password)}@${host}:${port}/${database}${sslMode}`;
}

export const config = {
  NODE_ENV: process.env.NODE_ENV || 'development',
  LOG_LEVEL: process.env.LOG_LEVEL || (process.env.NODE_ENV === 'production' ? 'info' : 'debug'),
  PORT: parseInt(process.env.PORT || '8000', 10),

  // DB
  DATABASE_URL: process.env.DATABASE_URL || buildDatabaseUrlFromParts(),

  // Auth
  JWT_SECRET: process.env.JWT_SECRET || 'dev-secret-change-me',
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '7d',

  // CORS
  CORS_ORIGIN: process.env.CORS_ORIGIN || '*',
};
