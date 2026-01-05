# System Patterns

## Architecture Overview
- Generated project with app/frontend, app/backend, app/database, docker/
- REST API backend with JWT auth and PostgreSQL persistence
- SPA frontend consuming backend API

## Design Patterns
- Backend: route/controller separation, validation + centralized error handling
- Frontend: pages/components with shared layout, loading/error states

## Component Relationships
- Frontend routes -> pages -> components -> API client -> backend endpoints
- Backend routes -> controllers -> db queries -> postgres

## Key Technical Decisions
- Keep file operations within workspace; avoid duplicates/out-of-root writes
- Use consistent naming for routes/models; prefer schema-aligned field names

## API Patterns
- JSON REST under /api/*
- Authorization: Bearer <token> for protected routes
