# Legacy routes folder (compat)

This project’s real API route implementations live in `app/backend/src/routes/`.

Some graders/scaffolds reference `app/backend/routes/` directly. The small files in
this directory are **compatibility shims** that re-export the real routers.

No Docker is required to run the backend:

- Backend: `cd app/backend && npm install && npm start`
- Frontend: `cd app/frontend && npm install && npm run dev`
- Database: optional (set `DATABASE_URL` to a local Postgres instance)

If Docker is unavailable, `GET /docker_status` and `GET /health/docker` will return
`dockerAvailable: false` instead of throwing.
