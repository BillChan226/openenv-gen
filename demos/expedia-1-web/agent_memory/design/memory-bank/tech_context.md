# Technical Context

## Technology Stack
- Frontend: React
- Backend: Node.js/Express
- Database: PostgreSQL

## Dependencies (adjust per package.json)
- Frontend: router/build tooling, lint tooling as applicable
- Backend: Express, JWT auth, PostgreSQL client, dotenv

## Development Setup
- Prefer docker compose when available
- Otherwise run backend + frontend locally with node + postgres

## Technical Constraints
- Keep paths within workspace root; no writes outside generated project
- Deterministic, testable APIs; clear error handling

## Environment Variables
- DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD/DB_NAME/DB_PORT
- PORT / CORS_ORIGIN / VITE_API_BASE (align UI/API ports)
- Provider keys (OPENAI_API_KEY etc.) if needed
