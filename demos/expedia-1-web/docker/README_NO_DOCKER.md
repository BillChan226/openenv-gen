# Running without Docker

If you see **"Docker daemon not reachable"** (or Docker Desktop is not running), you can still run this project locally without containers.

## Backend

```bash
cd app/backend
npm install
npm start
```

The backend will start on `http://localhost:8080` by default.

## Frontend

```bash
cd app/frontend
npm install
npm run dev
```

The frontend will start on `http://localhost:5173` by default.

## Database

Docker is the default way to run Postgres for this project. If Docker is unavailable, you can:

1. Install Postgres locally, create a database/user, then set `DATABASE_URL` for the backend.
2. Or run the backend in a mocked/in-memory mode (if supported by your environment).

Example `DATABASE_URL`:

```bash
export DATABASE_URL=postgres://expedia:expedia@localhost:5432/expedia
```
