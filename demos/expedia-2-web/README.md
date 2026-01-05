# Expedia-Style Travel Booking Platform

This repo contains a full-stack Expedia-inspired travel booking app.

## Quick start (no Docker)

If Docker is not available in your environment (e.g. `Cannot connect to the Docker daemon ... docker.sock`), you can run everything directly with Node + a local Postgres.

### 1) Start PostgreSQL (local)

Create a database called `app` and a user/password `postgres/postgres` (or adjust env vars below).

Initialize schema + seed:

```bash
psql "postgres://postgres:postgres@localhost:5432/app" -f app/database/init/01_schema.sql
psql "postgres://postgres:postgres@localhost:5432/app" -f app/database/init/02_seed.sql
```

### 2) Start backend

```bash
cd app/backend
npm install

# configure DB connection
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/app"
export PORT=8082

npm start
```

Health check:

```bash
curl http://localhost:8082/health
```

### 3) Start frontend

```bash
cd app/frontend
npm install

# point frontend to backend
export VITE_API_PROXY_TARGET="http://localhost:8082"

npm run dev
```

Open: http://localhost:5173

## Docker (optional)

If you *do* have Docker running, you can use:

```bash
docker compose -f docker/docker-compose.yml up --build
```

- Frontend: http://localhost:8000
- Backend: http://localhost:3000
- Postgres: localhost:5432
