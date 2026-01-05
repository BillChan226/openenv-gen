# Database bootstrap (local QA/dev)

This backend expects a PostgreSQL database. Some routes assume tables exist.

To unblock local runs/QA when you are **not** using Docker Compose, this repo includes an **idempotent bootstrap** that creates the required tables (and optionally seeds a few rows).

## 1) Configure DB connection

Use either `DATABASE_URL` or discrete `DB_*` env vars.

### Option A: DATABASE_URL

```bash
export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/voyager
```

### Option B: DB_* env vars

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=voyager
```

## 2) Run bootstrap script

From `app/backend`:

```bash
npm run bootstrap:db
```

To disable seeding:

```bash
SEED_DB=false npm run bootstrap:db
```

## 3) Auto-bootstrap on server start (optional)

You can also have the API create tables at startup:

```bash
BOOTSTRAP_DB=true npm start
```

Optional: disable seeding at startup:

```bash
BOOTSTRAP_DB=true SEED_DB=false npm start
```

## Notes

- The bootstrap is **safe to run multiple times** (`CREATE TABLE IF NOT EXISTS`).
- If Postgres is not reachable, the server will still start but DB-dependent routes return `503`.
