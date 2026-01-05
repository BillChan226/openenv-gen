#!/usr/bin/env node

require('dotenv').config();

const db = require('../src/db');
const { bootstrap } = require('../src/db/bootstrap');

(async () => {
  const ok = await db.isAvailable();
  if (!ok) {
    // eslint-disable-next-line no-console
    console.error('Database is not reachable. Set DATABASE_URL or DB_* env vars and ensure Postgres is running.');
    process.exit(1);
  }

  await bootstrap({ withSeed: String(process.env.SEED_DB || 'true').toLowerCase() === 'true' });
  // eslint-disable-next-line no-console
  console.log('Bootstrap complete');
  process.exit(0);
})().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
